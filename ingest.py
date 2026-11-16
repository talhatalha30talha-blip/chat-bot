# ingest.py
import os
import shutil
from typing import List, Optional
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

PERSIST_DIRECTORY = "./chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def is_knowledge_base_ready() -> bool:
    """Checks if ./chroma_db exists and already contains vector chunks."""
    if not os.path.exists(PERSIST_DIRECTORY):
        return False
    try:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        vector_store = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=embeddings
        )
        return vector_store._collection.count() > 0
    except Exception:
        return False


def ingest_sources(
    urls: Optional[List[str]] = None,
    file_paths: Optional[List[str]] = None,
    raw_text: Optional[str] = None,
    reset_existing: bool = True
) -> dict:
    """Ingests URLs, uploaded files (PDF/TXT/MD/CSV), and/or raw text from the UI setup into ./chroma_db."""
    docs: List[Document] = []

    # 1. Load website URLs provided in the setup UI
    if urls:
        clean_urls = [u.strip() for u in urls if u.strip()]
        if clean_urls:
            loader = WebBaseLoader(clean_urls)
            docs.extend(loader.load())

    # 2. Load uploaded documents (.pdf, .txt, .md, .csv)
    if file_paths:
        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".pdf":
                docs.extend(PyPDFLoader(path).load())
            else:
                docs.extend(TextLoader(path, encoding="utf-8", autodetect_encoding=True).load())

    # 3. Load raw custom business information
    if raw_text and raw_text.strip():
        docs.append(Document(page_content=raw_text.strip(), metadata={"source": "custom_setup_text"}))

    if not docs:
        raise ValueError("Please provide at least one valid URL, document, or text block.")

    if reset_existing and os.path.exists(PERSIST_DIRECTORY):
        shutil.rmtree(PERSIST_DIRECTORY)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIRECTORY
    )

    return {
        "status": "success",
        "documents_loaded": len(docs),
        "chunks_created": len(chunks)
    }