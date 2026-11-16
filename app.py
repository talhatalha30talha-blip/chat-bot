import os
import json
import tempfile
import importlib
from typing import List, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

import graph as graph_module
from ingest import ingest_sources, is_knowledge_base_ready

load_dotenv()

SETUP_PIN = os.getenv("SETUP_PIN", "1234")
CONFIG_FILE = "./widget_config.json"


def load_widget_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "bot_name": "AI Assistant",
        "company_name": "our company",
        "welcome_message": "Hi there! How can I help you today?",
        "primary_color": "#2563eb",
    }


def save_widget_config(data: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Embeddable RAG Chat Widget", lifespan=lifespan)

# Allow any external website (WordPress, React, plain HTML, etc.) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


@app.get("/")
def serve_ui():
    """Serve the HTML chat interface at the root URL."""
    return FileResponse("static/index.html")


@app.get("/widget.js")
def serve_widget_js():
    """Serve the single-file embeddable chat bubble widget."""
    return FileResponse("static/widget.js", media_type="application/javascript")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def widget_status():
    """Returns whether first-time setup is completed """
    config = load_widget_config()
    return {
        "is_configured": is_knowledge_base_ready(),
        "bot_name": config.get("bot_name", "AI Assistant"),
        "company_name": config.get("company_name", ""),
        "welcome_message": config.get("welcome_message", "Hi there! How can I help you today?"),
        "primary_color": config.get("primary_color", "#2563eb"),
    }


@app.post("/setup")
async def setup_widget(
    pin: str = Form(...),
    bot_name: str = Form("AI Assistant"),
    company_name: str = Form("our company"),
    welcome_message: str = Form("Hi there! How can I help you today?"),
    primary_color: str = Form("#2563eb"),
    urls: str = Form(""),
    raw_text: str = Form(""),
    reset_existing: bool = Form(True),
    files: Optional[List[UploadFile]] = File(None),
):
    """First-time setup endpoint: ingests URLs, documents, and custom text into ChromaDB."""
    if pin != SETUP_PIN:
        raise HTTPException(status_code=401, detail="Invalid Setup PIN.")

    url_list = [u.strip() for u in urls.splitlines() if u.strip()]
    temp_paths = []

    try:
        if files:
            for upload in files:
                if upload.filename:
                    suffix = os.path.splitext(upload.filename)[1]
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                    tmp.write(await upload.read())
                    tmp.close()
                    temp_paths.append(tmp.name)

        result = ingest_sources(
            urls=url_list,
            file_paths=temp_paths,
            raw_text=raw_text,
            reset_existing=reset_existing,
        )

        save_widget_config({
            "bot_name": bot_name,
            "company_name": company_name,
            "welcome_message": welcome_message,
            "primary_color": primary_color,
        })

        importlib.reload(graph_module)

        return {"status": "configured", "details": result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)


@app.post("/chat")
def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    result = graph_module.graph.invoke(
        {"messages": [HumanMessage(content=req.message)]},
        config=config,
    )
    reply = result["messages"][-1].content
    return {"reply": reply, "thread_id": req.thread_id}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}

    async def event_generator():
        async for event in graph_module.graph.astream_events(
            {"messages": [HumanMessage(content=req.message)]},
            config=config,
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield f"data: {json.dumps({'token': chunk.content})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")