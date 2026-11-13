import os
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Directory where Chroma vector store will save data locally
PERSIST_DIRECTORY = "./chroma_db"

def ingest_website(url: str):
    print(f"1. Fetching content from website: {url}...")
    loader = WebBaseLoader(url)
    docs = loader.load()
    
    print(f"2. Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks.")

    print(f"3. Generating local free embeddings and storing in ChromaDB...")
    
    # 100% Free, runs locally on your machine, no API key needed!
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Store locally in Chroma
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIRECTORY
    )
    
    print(f"SUCCESS: Website successfully ingested and saved to local vector store at '{PERSIST_DIRECTORY}'!")

if __name__ == "__main__":
    target_url = "https://www.qualityresourcellc.com/"
    ingest_website(target_url)