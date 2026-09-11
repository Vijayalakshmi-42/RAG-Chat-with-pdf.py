import os,re,asyncio,tempfile,pymupdf,chromadb,flet as ft
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

class PDFLoader:
    def __init__(self): self.splitter=RecursiveCharacterTextSplitter(chunk_size=800,chunk_overlap=120,separators=["\n\n","\n",". "," ",""])
    def clean(self,text): return re.sub(r"\s+"," ",str(text or "")).strip()
    def split(self,text,page,path): return [{"text":c,"metadata":{"page":page,"source":os.path.basename(path)}} for c in [self.clean(x) for x in self.splitter.split_text(self.clean(text))] if len(c)>=20]
    def load_pymupdf(self,path):
        chunks=[]; doc=pymupdf.open(path)
        try:
            if doc.needs_pass: raise ValueError("PDF is password protected.")
            for n,page in enumerate(doc,1):
                try: text=page.get_text("text",sort=True) or ""
                except Exception: text=""
                if self.clean(text): chunks.extend(self.split(text,n,path))
        finally: doc.close()
        return chunks
    def load_pypdf(self,path):
        chunks=[]; reader=PdfReader(path,strict=False)
        if reader.is_encrypted:
            try: reader.decrypt("")
            except Exception: raise ValueError("PDF is password protected.")
        for n,page in enumerate(reader.pages,1):
            try: text=page.extract_text() or ""
            except Exception: text=""
            if self.clean(text): chunks.extend(self.split(text,n,path))
        return chunks
    def load(self,path):
        chunks=[]
        try: chunks=self.load_pymupdf(path)
        except Exception: pass
        if not chunks:
            try: chunks=self.load_pypdf(path)
            except Exception: pass
        chunks=[x for x in chunks if x["text"].strip()]
        if not chunks: raise ValueError("No readable text found. OCR is required for scanned or image-only PDFs.")
        return chunks

class AddDocumentsToDB:
    def __init__(self): self.client=chromadb.EphemeralClient(); self.name="pdf_documents"; self.embedding=DefaultEmbeddingFunction(); self.collection=self.client.get_or_create_collection(name=self.name,embedding_function=self.embedding)
    def reset(self):
        try: self.client.delete_collection(self.name)
        except Exception: pass
        self.collection=self.client.get_or_create_collection(name=self.name,embedding_function=self.embedding)
    def add_batch(self,chunks,start,end): batch=chunks[start:end]; self.collection.add(ids=[f"chunk_{i}" for i in range(start,end)],documents=[x["text"] for x in batch],metadatas=[x["metadata"] for x in batch])
    def count(self): return self.collection.count()
    def query(self,text):
        count=self.collection.count()
        if count==0: return []
        r=self.collection.query(query_texts=[text],n_results=min(5,count),include=["documents","metadatas","distances"]); docs=(r.get("documents") or [[]])[0]; metas=(r.get("metadatas") or [[]])[0]; distances=(r.get("distances") or [[]])[0]
        return [{"document":str(d).strip(),"metadata":metas[i] if i<len(metas) and metas[i] else {},"distance":distances[i] if i<len(distances) else None} for i,d in enumerate(docs) if d is not None and str(d).strip()]

class MainPage:
    def __init__(self,page:ft.Page):
        self.page=page; self.uploaded_file=None; self.temp_pdf=None; self.pdf_ready=False; self.history={}; self.pdf_loader=PDFLoader(); self.db=AddDocumentsToDB()
        self.query_field=ft.TextField(hint_text="Ask something from your PDF...",expand=True,border_radius=20,on_submit=self.search_pdf)
        self.send_button=ft.IconButton(icon=ft.Icons.SEND_ROUNDED,icon_color=ft.Colors.WHITE,bgcolor=ft.Colors.PURPLE,on_click=self.search_pdf)
        self.result_list=ft.ListView(expand=True,spacing=12,padding=10)
        self.empty_chat=ft.Container(expand=True,alignment=ft.Alignment.CENTER,content=ft.Column(alignment=ft.MainAxisAlignment.CENTER,horizontal_alignment=ft.CrossAxisAlignment.CENTER,controls=[ft.Icon(ft.Icons.PICTURE_AS_PDF,size=75,color=ft.Colors.RED),ft.Text("You Haven't Uploaded Any PDF Yet",size=20,weight=ft.FontWeight.BOLD),ft.Text("Tap + to select a PDF",color=ft.Colors.GREY)]))
        self.chat_stack=ft.Stack(expand=True,controls=[ft.Container(expand=True,padding=ft.Padding.only(bottom=85),content=self.result_list),ft.Container(left=10,right=10,bottom=10,padding=10,bgcolor=ft.Colors.WHITE,border_radius=25,shadow=ft.BoxShadow(blur_radius=15,color=ft.Colors.with_opacity(0.15,ft.Colors.BLACK)),content=ft.Row(controls=[self.query_field,self.send_button]))])
        self.app_bar=ft.AppBar(leading=ft.Icon(ft.Icons.MENU,size=30),title=ft.Text("CHAT WITH PDF",weight=ft.FontWeight.BOLD,font_family="Consolas"),center_title=True,bgcolor=ft.Colors.YELLOW,color=ft.Colors.BLACK,elevation=10)
        self.navigation_bar=ft.NavigationBar(selected_index=0,bgcolor=ft.Colors.PINK,indicator_color=ft.Colors.WHITE,on_change=self.change_mode,destinations=[ft.NavigationBarDestination(icon=ft.Icons.CHAT,label="Chat Mode"),ft.NavigationBarDestination(icon=ft.Icons.VISIBILITY,label="View Mode"),ft.NavigationBarDestination(icon=ft.Icons.HISTORY,label="History Mode")])
        self.fab=ft.FloatingActionButton(icon=ft.Icons.ADD,mini=True,bgcolor=ft.Colors.PINK,on_click=self.pick_pdf)
        self.body=ft.Container(expand=True,padding=10)
        self.architecture_image=ft.Container(padding=8,bgcolor=ft.Colors.WHITE,border=ft.Border.all(2,ft.Colors.BLUE_400),border_radius=20,shadow=ft.BoxShadow(spread_radius=2,blur_radius=18,color=ft.Colors.with_opacity(0.2,ft.Colors.BLACK),offset=ft.Offset(0,5)),content=ft.Image(src="./assets/project_architecture.png",fit=ft.BoxFit.CONTAIN,border_radius=15))
        self.view_content=ft.Container(padding=22,bgcolor=ft.Colors.WHITE,border_radius=20,border=ft.Border.all(1,ft.Colors.GREY_300),shadow=ft.BoxShadow(blur_radius=14,color=ft.Colors.with_opacity(0.12,ft.Colors.BLACK)),content=ft.Column(spacing=18,controls=[ft.Text("CHAT WITH PDF",size=30,weight=ft.FontWeight.BOLD,color=ft.Colors.BLUE_900,text_align=ft.TextAlign.CENTER),ft.Text("AI Powered PDF Retrieval Application",size=18,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_700,text_align=ft.TextAlign.CENTER),ft.Divider(),ft.Text("Project Overview",size=22,weight=ft.FontWeight.BOLD,color=ft.Colors.BLUE_900),ft.Text("Chat With PDF is a document retrieval application built using Flet, PyMuPDF, pypdf, LangChain text splitters and ChromaDB. The application allows a user to upload a PDF, automatically extract its text, divide the document into meaningful chunks, generate vector embeddings, store them inside an in-memory vector database and retrieve the five most relevant document sections for every user query.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("1. Flet User Interface",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("Flet is used to create the complete graphical user interface. The application contains Chat Mode, View Mode and History Mode. The floating action button allows the user to select a PDF. NavigationBar is used to switch between the three modes. Chat Mode uses Stack so that the query box remains fixed at the bottom while retrieved document cards remain vertically scrollable above it.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("2. PDF Selection And Upload",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("When the user taps the + floating action button, Flet FilePicker opens and allows one PDF file to be selected. The selected PDF is read as bytes and temporarily written into the operating system temporary directory. A progress SnackBar is displayed while the bytes are being written, so the interface remains responsive during the upload stage.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("3. Primary PDF Loader - PyMuPDF",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("The application first uses PyMuPDF to extract PDF text. The document is opened using pymupdf.open(). Every page is processed using page.get_text('text', sort=True). PyMuPDF is used as the primary loader because it is lightweight, fast and generally performs well with ordinary text-based PDF files.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("4. Fallback PDF Loader - pypdf",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("If PyMuPDF does not return usable text, the application automatically uses pypdf as a fallback. PdfReader(path, strict=False) opens the document and page.extract_text() attempts to extract text from each page. strict=False makes the reader more tolerant of some malformed PDF structures. If both readers fail to produce readable text, the document is probably scanned, image-only, damaged or protected. Scanned PDFs require OCR because their visible text is stored as images rather than text objects.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("5. Cleaning The Extracted Text",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("The extracted page content is passed through a clean() method. Regular expressions remove repeated spaces, tabs and line breaks. Empty content is ignored. This ensures that blank strings and unusable text are not stored inside the vector database.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("6. LangChain Text Splitting",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("RecursiveCharacterTextSplitter from langchain-text-splitters divides each page into smaller text chunks. The application currently uses chunk_size=800 and chunk_overlap=120. Chunk size controls approximately how much text is stored in one vector document. Chunk overlap keeps some text shared between neighboring chunks so important context near a chunk boundary is less likely to be lost.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("7. Document Metadata",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("Every generated chunk contains both text and metadata. Metadata stores the page number and original PDF filename. This information is later returned by ChromaDB and allows each search result card to show exactly which PDF page the retrieved information came from.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("8. ChromaDB EphemeralClient",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("The application directly uses chromadb rather than a LangChain vector-store wrapper. chromadb.EphemeralClient() creates an in-memory vector database. This database exists only while the application process is running. When the application closes, the stored vectors disappear automatically. This is suitable for a temporary PDF search application because the uploaded document does not need to remain permanently stored.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("9. ChromaDB Default Embedding Function",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("DefaultEmbeddingFunction is assigned directly to the ChromaDB collection. When text chunks are inserted through collection.add(), Chroma automatically converts every document into a vector embedding. An embedding is a numerical representation of the semantic meaning of text. Text with similar meanings normally produces vectors located closer together in vector space.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("10. Adding Chunks To The Database",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("Before indexing a new PDF, the previous Chroma collection is deleted and recreated. Valid chunks are then inserted in batches of 32. Every chunk receives a unique ID, document text and page metadata. Batch insertion allows the application to update the progress bar while ChromaDB generates embeddings and inserts the vectors.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("11. Asynchronous Processing",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("Operations such as PDF parsing, vector generation, database insertion and vector searching can take time. The application therefore uses async event handlers together with asyncio.to_thread(). Blocking operations are moved away from Flet's main event loop so progress indicators, SnackBars and other interface elements can continue updating while processing is taking place.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("12. Query Processing",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("After the PDF has been indexed, Chat Mode displays a TextField and send button. The user enters a natural-language query. The query text is passed directly to the ChromaDB collection using query_texts. Because the collection already has DefaultEmbeddingFunction, ChromaDB automatically creates an embedding for the query before searching the stored vectors.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("13. Vector Similarity Search",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("collection.query() compares the vector representation of the user's query against every stored document vector. The application requests up to five results using n_results=5. ChromaDB returns the closest matching documents together with their metadata and distance values. Smaller vector distance generally represents a more similar semantic match.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("14. Displaying Retrieved Documents",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("Each retrieved document is displayed inside a Flet Card. The card contains a Relevant Document heading, the page number, the complete retrieved text and its vector distance. The result cards are placed inside ListView so they can scroll vertically while the query input remains available at the bottom of Chat Mode.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("15. History Mode",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Text("Search history is stored using self.history, which is a Python dictionary. Each query becomes a dictionary key and its retrieved list of document dictionaries becomes the value. History Mode iterates through this dictionary and displays each previous query followed by the documents that were retrieved for it.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY),ft.Text("16. Complete Application Flow",size=21,weight=ft.FontWeight.BOLD,color=ft.Colors.PURPLE_900),ft.Container(padding=18,bgcolor=ft.Colors.BLUE_50,border_radius=15,content=ft.Text("Select PDF → Read PDF Bytes → Save Temporary PDF → PyMuPDF Text Extraction → pypdf Fallback If Required → Clean Extracted Text → RecursiveCharacterTextSplitter → Create Text Chunks → Attach Page Metadata → Create ChromaDB EphemeralClient → DefaultEmbeddingFunction Generates Embeddings → Add Chunks In Batches → User Enters Query → Query Embedding Generated → Similarity Search → Retrieve Top 5 Documents → Display Results As Cards → Save Query And Documents In History.",size=16,weight=ft.FontWeight.BOLD,color=ft.Colors.BLUE_900,text_align=ft.TextAlign.JUSTIFY)),ft.Text("Project Summary",size=22,weight=ft.FontWeight.BOLD,color=ft.Colors.BLUE_900),ft.Text("This project forms a complete lightweight Retrieval system for PDF documents. Flet manages the application interface, PyMuPDF and pypdf handle document extraction, RecursiveCharacterTextSplitter prepares searchable text chunks and ChromaDB handles embeddings, vector storage and semantic retrieval. The architecture remains simple because the application communicates directly with ChromaDB without introducing an additional LangChain vector-store layer.",size=16,color=ft.Colors.GREY_800,text_align=ft.TextAlign.JUSTIFY)]))

    async def main(self): self.page.title="Chat With PDF"; self.page.padding=10; self.page.appbar=self.app_bar; self.page.navigation_bar=self.navigation_bar; self.page.floating_action_button=self.fab; self.page.add(self.body); self.render()

    def render(self): self.body.content=self.chat_stack if self.navigation_bar.selected_index==0 and self.pdf_ready else self.empty_chat if self.navigation_bar.selected_index==0 else self.build_view_mode() if self.navigation_bar.selected_index==1 else self.build_history_mode(); self.page.update()

    def build_view_mode(self): return ft.ListView(expand=True,spacing=20,padding=10,controls=[self.architecture_image,self.view_content])

    def build_history_mode(self):
        if not self.history: return ft.Container(expand=True,alignment=ft.Alignment.CENTER,content=ft.Text("No Search History Available",size=22,weight=ft.FontWeight.BOLD))
        items=[]
        for query,documents in self.history.items(): items.append(ft.Container(padding=15,bgcolor=ft.Colors.PURPLE_50,border_radius=18,content=ft.Column(spacing=12,controls=[ft.Row(controls=[ft.Icon(ft.Icons.SEARCH,color=ft.Colors.PURPLE),ft.Text(query,size=18,weight=ft.FontWeight.BOLD,expand=True)]),*[self.document_card(i+1,d) for i,d in enumerate(documents)]])))
        return ft.ListView(expand=True,spacing=18,padding=10,controls=items)

    def change_mode(self,e): self.render()

    async def show_progress(self,title,value=None): p=ft.ProgressBar(value=value,bar_height=5); b=ft.SnackBar(duration=600000,bgcolor=ft.Colors.WHITE,content=ft.Column(tight=True,spacing=7,controls=[ft.Text(title,color=ft.Colors.BLACK,weight=ft.FontWeight.BOLD),p])); self.page.show_dialog(b); self.page.update(); await asyncio.sleep(0); return b,p

    async def close_progress(self,b): b.open=False; self.page.update(); await asyncio.sleep(0.1)

    async def write_pdf(self,data,path,p):
        total=len(data); step=max(65536,total//50); done=0
        with open(path,"wb") as f:
            for i in range(0,total,step): block=data[i:i+step]; await asyncio.to_thread(f.write,block); done+=len(block); p.value=min(done/total,1); self.page.update(); await asyncio.sleep(0)

    async def add_chunks(self,chunks,p):
        await asyncio.to_thread(self.db.reset); total=len(chunks); batch_size=32
        for start in range(0,total,batch_size): end=min(start+batch_size,total); await asyncio.to_thread(self.db.add_batch,chunks,start,end); p.value=end/total; self.page.update(); await asyncio.sleep(0)
        return self.db.count()

    async def pick_pdf(self,e):
        files=await ft.FilePicker().pick_files(file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=["pdf"],allow_multiple=False,with_data=True)
        if not files: return
        selected=files[0]
        if not selected.bytes: self.show_error("Could not read selected PDF."); return
        self.uploaded_file=selected; self.pdf_ready=False; self.navigation_bar.selected_index=0; self.render(); bar=None
        try:
            bar,p=await self.show_progress(f"Uploading {selected.name}",0); self.temp_pdf=os.path.join(tempfile.gettempdir(),f"chatpdf_{selected.name}"); await self.write_pdf(selected.bytes,self.temp_pdf,p); p.value=1; self.page.update(); await asyncio.sleep(0.2); await self.close_progress(bar)
            bar,p=await self.show_progress("Loading And Splitting PDF"); chunks=await asyncio.to_thread(self.pdf_loader.load,self.temp_pdf); p.value=1; self.page.update(); await asyncio.sleep(0.2); await self.close_progress(bar)
            bar,p=await self.show_progress(f"Adding {len(chunks)} Chunks To ChromaDB",0); count=await self.add_chunks(chunks,p); p.value=1; self.page.update(); await asyncio.sleep(0.2); await self.close_progress(bar)
            self.pdf_ready=True; self.history={}; self.result_list.controls=[ft.Container(padding=15,bgcolor=ft.Colors.GREEN_50,border_radius=15,content=ft.Row(controls=[ft.Icon(ft.Icons.CHECK_CIRCLE,color=ft.Colors.GREEN),ft.Column(expand=True,controls=[ft.Text(selected.name,weight=ft.FontWeight.BOLD),ft.Text(f"{count} valid chunks indexed successfully")])]))]; self.render(); self.page.show_dialog(ft.SnackBar(bgcolor=ft.Colors.GREEN_700,content=ft.Text("PDF Ready For Searching",color=ft.Colors.WHITE)))
        except Exception as ex:
            self.pdf_ready=False
            if bar:
                try: await self.close_progress(bar)
                except Exception: pass
            self.show_error(f"PDF processing failed: {ex}")

    def document_card(self,index,item):
        text=str(item.get("document") or "").strip(); page_no=item.get("metadata",{}).get("page","?"); similarity=item.get("distance")
        controls=[ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[ft.Text(f"Relevant Document {index}",size=17,weight=ft.FontWeight.BOLD,color=ft.Colors.BLUE_900),ft.Container(padding=7,bgcolor=ft.Colors.BLUE_50,border_radius=10,content=ft.Text(f"Page {page_no}",size=12,color=ft.Colors.BLACK))]),ft.Divider(),ft.Container(width=float("inf"),padding=5,content=ft.Text(value=text,size=15,color=ft.Colors.BLACK,selectable=True,text_align=ft.TextAlign.JUSTIFY))]
        if similarity is not None: controls.append(ft.Text(f"Distance: {float(similarity):.4f}",size=11,color=ft.Colors.GREY_600))
        return ft.Card(elevation=3,content=ft.Container(padding=16,bgcolor=ft.Colors.WHITE,content=ft.Column(spacing=10,controls=controls)))

    async def search_pdf(self,e):
        query=(self.query_field.value or "").strip()
        if not query or not self.pdf_ready: return
        self.query_field.value=""; self.result_list.controls=[ft.Container(padding=12,bgcolor=ft.Colors.PURPLE_50,border_radius=15,content=ft.Text(query,size=17,weight=ft.FontWeight.BOLD,color=ft.Colors.BLACK)),ft.ProgressBar(value=None)]; self.page.update()
        try:
            docs=await asyncio.to_thread(self.db.query,query); self.result_list.controls=self.result_list.controls[:1]
            if not docs: self.result_list.controls.append(ft.Text("No relevant documents were returned.",color=ft.Colors.RED))
            else:
                for i,d in enumerate(docs,1): self.result_list.controls.append(self.document_card(i,d))
                self.history[query]=docs
            self.page.update()
        except Exception as ex: self.result_list.controls=self.result_list.controls[:1]; self.result_list.controls.append(ft.Text(f"Search error: {ex}",color=ft.Colors.RED)); self.page.update()

    def show_error(self,message): self.page.show_dialog(ft.SnackBar(bgcolor=ft.Colors.RED_700,content=ft.Text(message,color=ft.Colors.WHITE))); self.page.update()

async def main(page:ft.Page): app=MainPage(page); await app.main()

ft.run(main)