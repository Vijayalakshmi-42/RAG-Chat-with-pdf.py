📄 Chat With PDF – RAG Project

A simple **Retrieval-Augmented Generation (RAG)** application that allows users to upload a PDF document and ask questions about its content using natural language.

The application extracts text from the PDF, divides it into smaller chunks, creates embeddings, stores them in a vector database, and retrieves the most relevant information for user queries.

---

🚀 Features

* 📂 Upload PDF documents
* 📖 Extract text from PDF files
* 🔍 Split large documents into smaller chunks
* 🧹 Clean and preprocess extracted text
* 🧠 Generate embeddings for document chunks
* 🗄️ Store document embeddings using ChromaDB
* 💬 Ask questions about the uploaded PDF
* 📑 Retrieve relevant information based on the question
* 📄 Display document name and page number
* 🕐 Maintain chat history
* 🔐 Handle password-protected PDFs
* ⚡ Perform time-consuming operations asynchronously

---

🏗️ Project Workflow

```text
PDF Upload
    ↓
PDF Text Extraction
    ↓
Text Cleaning
    ↓
Text Chunking
    ↓
Embedding Generation
    ↓
ChromaDB Vector Storage
    ↓
User Question
    ↓
Similarity Search
    ↓
Relevant Document Chunks
    ↓
Answer with Source Information
```

---

🛠️ Technologies Used

| Technology               | Purpose                     |
| ------------------------ | --------------------------- |
| Python                   | Core programming language   |
| Flet                     | User interface              |
| PyMuPDF                  | Primary PDF text extraction |
| pypdf                    | PDF processing fallback     |
| LangChain Text Splitters | Document chunking           |
| ChromaDB                 | Vector database             |
| Regex                    | Text cleaning               |
| Asyncio                  | Asynchronous operations     |

---

Libraries Used

```text
flet
pymupdf
pypdf
langchain-text-splitters
chromadb
```

Install the required libraries using:

```bash
pip install flet pymupdf pypdf langchain-text-splitters chromadb
```

---

📁 Project Structure

```text
Chat-With-PDF/
│
├── main.py
├── assets/
│   └── project_architecture.png
├── requirements.txt
└── README.md
```

> The exact file structure may vary depending on your project files.

---

⚙️ How It Works

1. PDF Upload

The user selects a PDF document through the Flet interface.

2. Text Extraction

The application first uses **PyMuPDF** to extract text from each page.

If necessary, **pypdf** can be used as a fallback PDF reader.

3. Text Cleaning

Extracted text is cleaned using regular expressions to remove unnecessary whitespace.

### 4. Text Chunking

The extracted text is divided into smaller chunks using:

```text
Chunk Size: 800
Chunk Overlap: 120
```

This helps the application retrieve relevant sections efficiently.

5. Embedding and Storage

The document chunks are converted into embeddings using ChromaDB's default embedding function and stored in a ChromaDB collection.

Each chunk contains metadata such as:

```text
page
source
```

6. Question Answering

The user asks a question about the uploaded document.

The application performs a similarity search and retrieves the most relevant document chunks.

7. Source Information

The retrieved information includes the document name and page number, helping the user identify where the information came from.

---

🖥️ Application Modes

The application contains three main modes:

💬 Chat Mode

Allows users to ask questions about the uploaded PDF.

👁️ View Mode

Allows users to view information related to the uploaded document.

🕐 History Mode

Maintains the previous questions and responses during the application session.

---


---

▶️ How to Run

Step 1: Clone the repository

```bash
git clone https://github.com/YourUsername/Chat-With-PDF.git
```

Step 2: Open the project

```bash
cd Chat-With-PDF
```

Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

Or install them directly:

```bash
pip install flet pymupdf pypdf langchain-text-splitters chromadb
```
Step 4: Run the application

```bash
python main.py
```

---

📌 Use Cases

This project can be useful for:

* 📚 Research papers
* ⚖️ Legal documents
* 🏢 Company reports
* 📋 Business documents
* 📖 Study materials
* 📑 Technical documentation
* 🗂️ Large PDF collections

---

🎯 Problem Statement

Many important documents such as legal papers, research papers, reports, and company documents are stored as PDF files. Finding specific information manually from large PDF files can be time-consuming.

Traditional keyword-based search may not understand what the user is actually asking.

**Chat With PDF** provides a simple way to interact with PDF documents using natural-language questions and retrieve relevant information along with its document source and page number.

---
 🔮 Future Enhancements

* Support for multiple PDF documents
* Improved answer generation using an LLM
* Persistent vector database storage
* Better citation handling
* Support for additional document formats
* Cloud deployment
* Authentication and user accounts
* Improved chat interface
* Conversation export

---




