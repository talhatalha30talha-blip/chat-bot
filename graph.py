import os
import json
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage, AIMessage
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

CONFIG_FILE = "./widget_config.json"


def get_bot_identity() -> tuple[str, str]:
    """Reads bot_name and company_name saved by the first-time setup UI."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                bot_name = cfg.get("bot_name", "AI Assistant").strip() or "AI Assistant"
                company_name = cfg.get("company_name", "our company").strip() or "our company"
                return bot_name, company_name
        except Exception:
            pass
    return "AI Assistant", "our company"


class ChatState(TypedDict):
    """State shared across nodes in the graph."""
    messages: Annotated[list[AnyMessage], add_messages]


def build_graph() -> StateGraph:
    PERSIST_DIRECTORY = "./chroma_db"
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    if os.path.exists(PERSIST_DIRECTORY):
        vector_store = Chroma(
            persist_directory=PERSIST_DIRECTORY,
            embedding_function=embeddings
        )
        retriever = vector_store.as_retriever(
            search_kwargs={"k": 3}
        )
    else:
        retriever = None

    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME", "llama3-70b-8192"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1"),
        temperature=0.3
    )

    def chatbot_node(state: ChatState) -> dict:
        messages = state["messages"]
        latest_user_message = messages[-1].content if messages else ""

        context_text = ""
        if retriever:
            docs = retriever.invoke(latest_user_message)
            context_text = "\n\n".join([doc.page_content for doc in docs])

        bot_name, company_name = get_bot_identity()

        system_prompt = (
            f"You are {bot_name}, a specialized and professional customer support assistant "
            f"for {company_name}. You are an independent AI, NOT affiliated with OpenAI, ChatGPT, or any other company.\n\n"
            "Identity & Persona Rules:\n"
            f"- If asked who you are, always state that you are {bot_name}, the virtual assistant for {company_name}.\n"
            "- Never mention OpenAI, ChatGPT, or LLMs.\n"
            "- Keep your answers concise, direct, and strictly to the point. Answer as short as possible and to the point.\n\n"
            f"Context from website knowledge base:\n{context_text}"
        )

        full_messages = [SystemMessage(content=system_prompt)] + messages

        full_response = ""
        for chunk in llm.stream(full_messages):
            if chunk.content:
                full_response += chunk.content

        return {"messages": [AIMessage(content=full_response)]}

    workflow = StateGraph(ChatState)
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_edge(START, "chatbot")
    workflow.add_edge("chatbot", END)

    return workflow.compile(checkpointer=MemorySaver())


graph = build_graph()