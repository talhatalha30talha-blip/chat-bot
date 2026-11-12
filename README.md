# Quality Resource LLC Internal Simple Chatbot

A lightweight, reproducible internal chatbot built with **FastAPI**, **LangChain**, **LangGraph**, and **Docker** that answers employee questions about company products, policies, HR procedures, and general knowledge.

---

## Features

* **Stateful Conversations**: Multi-turn conversation memory powered by LangGraph's `MemorySaver` checkpointer, tracking context per `thread_id`.


* **Synchronous & Streaming Endpoints**: Supports both standard JSON responses (`POST /chat`) and real-time Server-Sent Events (SSE) streaming (`POST /chat/stream`).


* **OpenAI-Compatible Backend**: Configured to work seamlessly with Groq and any OpenAI-compatible API provider via environment variables.


* **One-Command Deployment**: Fully containerized using Docker and Docker Compose for instant cross-platform reproducibility.



---

## Tech Stack

* **Language**: Python 3.10+


* **Orchestration**: LangGraph (v1.0+ StateGraph)


* **Model Integration**: LangChain (`langchain-openai`)


* **Web Framework**: FastAPI & Uvicorn


* **Containerization**: Docker & Docker Compose



---

## Project Structure

```text
chat-bot/
├── graph.py          # LangGraph state machine definition
├── app.py            # FastAPI application routes & lifespan
├── Dockerfile        # Container build instructions
├── docker-compose.yml# Multi-container orchestration config
├── requirements.txt  # Python runtime dependencies
├── .env              # Local environment variables (API keys)
├── .env.example      # Template for environment configuration
└── README.md         # Project documentation

```

---

## Setup & Installation

### Prerequisites

* [Docker Engine](https://docs.docker.com/engine/install/) (24+) and [Docker Compose](https://docs.docker.com/compose/) (2.20+) installed on your machine.


* A valid API key for an OpenAI-compatible provider (e.g., Groq).



### 1. Configure Environment Variables

Create a file named `.env` in the root directory of the project based on the required template:

```env
OPENAI_API_KEY=your_actual_api_key_here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=openai/gpt-oss-20b

```

### 2. Run with Docker Compose

Build and start the application container using a single command:

```powershell
docker compose up --build

```

The API will be available at **`http://localhost:8000`**. Interactive OpenAPI documentation can be accessed at **`http://localhost:8000/docs`**.

---

## API Usage Examples (`curl`)

### 1. Health Check

Verify that the service is running and healthy:

```powershell
curl http://localhost:8000/health

```

### 2. Synchronous Chat (`POST /chat`)

Send a message and receive the complete response as JSON:

```powershell
curl -X POST http://localhost:8000/chat \
-H "Content-Type: application/json" \
-d '{"message": "What is the company leave policy?", "thread_id": "user-42"}'

```

### 3. Streaming Chat (`POST /chat/stream`)

Stream tokens incrementally using Server-Sent Events (SSE):

```powershell
curl -N -X POST http://localhost:8000/chat/stream \
-H "Content-Type: application/json" \
-d '{"message": "Summarise the leave policy in one sentence.", "thread_id": "user-42"}'

```

---

## Manual (Non-Docker) Local Run

If you prefer to run the application locally outside of Docker (requires Python 3.10+):

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI development server with Uvicorn
uvicorn app:app --reload

```