import os
from dotenv import load_dotenv
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# 1. Define State
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 2. Initialize Embeddings and Chroma Vector Store Retriever
PERSIST_DIRECTORY = "./chroma_db"
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Check if vector store exists before loading
if os.path.exists(PERSIST_DIRECTORY):
    vector_store = Chroma(
        persist_directory=PERSIST_DIRECTORY,
        embedding_function=embeddings
    )
    retriever = vector_store.as_retriever(
        search_kwargs={"k": 3} # Retrieve top 3 relevant chunks
    )
else:
    retriever = None

# 3. Initialize Groq Chat Model (via OpenAI-compatible wrapper)
llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME", "llama3-70b-8192"), # Replace with your active Groq model name
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1"),
    temperature=0.3
)

# 4. Define the RAG Chatbot Node
def chatbot_node(state: State):
    messages = state["messages"]
    latest_user_message = messages[-1].content if messages else ""
    
    # Retrieve relevant context from ChromaDB if available
    context_text = ""
    if retriever:
        docs = retriever.invoke(latest_user_message)
        context_text = "\n\n".join([doc.page_content for doc in docs])

    # Construct system prompt with website context
    system_prompt = (
        "You are a helpful AI assistant. Use the following context extracted from the target website "
        "to answer the user's question accurately. If the answer cannot be found in the context, "
        "rely on your general knowledge but mention that it wasn't explicitly found in the website content.\n\n"
        f"--- Website Context ---\n{context_text}\n------------------------"
    )

    # Combine system prompt with conversation history
    full_messages = [SystemMessage(content=system_prompt)] + messages
    
    response = llm.invoke(full_messages)
    return {"messages": [response]}

# 5. Build LangGraph Workflow
workflow = StateGraph(State)
workflow.add_node("chatbot", chatbot_node)
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)

# Compile graph with memory checkpointer
memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)