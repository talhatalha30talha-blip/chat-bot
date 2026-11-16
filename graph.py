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

load_dotenv(override=True)

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
        model=os.getenv("MODEL_NAME", "llama-3.1-8b-instant"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1"),
        temperature=0.1,
        max_tokens=180
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
            f"You are {bot_name}, the official customer support assistant for {company_name}.\n\n"
            "STRICT GUARDRAILS & RULES:\n"
            f"1. SCOPE LIMITATION: Answer ONLY questions directly related to {company_name}, its services, products, policies, or the provided knowledge base context below. "
            f"If the user asks about general knowledge, coding, math, news, or anything unrelated to {company_name}, politely refuse and say: "
            f"\"I can only answer questions related to {company_name} and our services.\"\n"
            f"2. NO HALLUCINATION: Use ONLY the context provided below. If the answer is not in the context, say you do not have that information and suggest contacting {company_name} directly.\n"
            "3. SHORT & DIRECT: Keep every answer extremely brief (maximum 2 to 3 short sentences or up to 3 short bullet points). Never write long paragraphs.\n"
            "4. TEXT ONLY (NO TABLES): Never use Markdown tables, pipe characters (|), or ASCII grids. Respond only in plain conversational text or simple short bullet points.\n"
            f"5. IDENTITY: Never mention OpenAI, ChatGPT, or AI models. You are {bot_name} for {company_name}.\n\n"
            f"Knowledge Base Context for {company_name}:\n"
            f"{context_text if context_text else 'No specific context found.'}"
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