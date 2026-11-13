# graph.py
import os
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# 1. Define State
class ChatState(TypedDict):
    """State shared across nodes in the graph."""
    messages: Annotated[list[AnyMessage], add_messages]

def build_graph() -> StateGraph:
    """Compile the RAG chatbot graph with vector retrieval and memory checkpointer."""
    
    # Initialize Embeddings and Chroma Vector Store Retriever
    PERSIST_DIRECTORY = "./chroma_db"
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

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

    # Initialize Groq / OpenAI-compatible Chat Model
    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME", "llama3-70b-8192"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1"),
        temperature=0.3
    )

    # Define the RAG Chatbot Node
    def chatbot_node(state: ChatState) -> dict:
        messages = state["messages"]
        latest_user_message = messages[-1].content if messages else ""
        
        # Retrieve relevant context from ChromaDB if available
        context_text = ""
        if retriever:
            docs = retriever.invoke(latest_user_message)
            context_text = "\n\n".join([doc.page_content for doc in docs])

        # Construct system prompt with proper context injection and persona rules
        system_prompt = (
            "You are Quality Resource AI, a specialized and professional customer support assistant "
            "for Quality Resource LLC. You are an independent AI, NOT affiliated with OpenAI, ChatGPT, or any other company.\n\n"
            "Identity & Persona Rules:\n"
            "- If asked who you are, always state that you are Quality Resource AI, the virtual assistant for Quality Resource LLC.\n"
            "- Never mention OpenAI, ChatGPT, or LLMs.\n"
            "- Keep your answers concise, direct, and strictly to the point.\n\n"
            f"Context from website knowledge base:\n{context_text}"
        )

        # Combine system prompt with conversation history
        full_messages = [SystemMessage(content=system_prompt)] + messages
        
        # Use llm.stream so tokens stream correctly through astream_events
        full_response = ""
        for chunk in llm.stream(full_messages):
            if chunk.content:
                full_response += chunk.content
                
        return {"messages": [AIMessage(content=full_response)]}

    # Build LangGraph Workflow
    workflow = StateGraph(ChatState)
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_edge(START, "chatbot")
    workflow.add_edge("chatbot", END)

    # Compile graph with memory checkpointer
    return workflow.compile(checkpointer=MemorySaver())

graph = build_graph()