# DocuRAG

Conversational assistant that answers technical questions using indexed official documentation as its only source of knowledge (local-first, no API keys required).

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-1C3C3C?style=flat-square&logo=langchain&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5.23-FF6B35?style=flat-square)
![Ollama](https://img.shields.io/badge/Ollama-Granite_3.2-000000?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135.1-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18.3.1-61DAFB?style=flat-square&logo=react&logoColor=black)

---

## What it does

DocuRAG indexes official technical documentation and lets you chat with it. Instead of searching through pages of docs, you ask a question in natural language and get an answer with sources shown separately in the UI.

<p align="center">
  <img src="./docurag_screenshot.jpg" alt="DocuRAG screenshot" width="920">
</p>

### Modes

- **RAG direct**: single-collection retrieval (optionally scoped by `technology`) + answer generation.
- **Smart agent**: multi-technology routing via `smart_search`, then synthesizes a single answer (this is the React UI "Agent" mode).
- **AG2 (experimental / legacy UI)**: AutoGen agent runner kept for experimentation (used by the Streamlit UI).

---

## Architecture

<p align="center">
  <img src="./rag_diagram.png" alt="RAG architecture diagram" width="920">
</p>

---

## Getting started

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/download) installed and running
- Node.js 18+ with npm (for the React UI)

### 1) Create a virtualenv and install deps

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

### 2) Pull the models

```bash
ollama pull granite3.2:latest
ollama pull nomic-embed-text:latest
```

### 3) Ingest documentation

```bash
python scripts/ingest.py fastapi
python scripts/ingest.py python
```

This scrapes the official documentation, chunks it, embeds it, and stores vectors in `data/chroma_db/` (git-ignored).

---

## Run (recommended): API + React UI

### 1) Start the API

```bash
uvicorn src.api.app:app --reload --port 8000
```

Verify: open `http://localhost:8000/docs`.

### 2) Start the React UI

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### UI behavior notes

- Sources are rendered in the UI (not injected into the answer text).
- The primary action toggles **Send/Stop**. Stop cancels the in-flight request (AbortController).
- Chat sessions can be renamed and deleted (client-side only).
- The UI shows `RAG` vs `Agent` mode:
  - `RAG`: uses `POST /api/v1/chat` with `mode="rag"` and optional `technology`.
  - `Agent`: uses `mode="agent"` and runs `smart_search` for deterministic multi-tech routing.

---

## Optional: Streamlit UI (legacy)

```bash
streamlit run src/ui/streamlit_app.py
```

Open `http://localhost:8501`.

---

## API

Primary endpoints (used by the React UI):

- `POST /api/v1/chat`
  - body: `{ "message": "...", "technology": "fastapi|python|null", "mode": "rag|agent" }`
  - returns: `{ "answer": "...", "sources": [{ "url": "...", "section": "...", "technology": "..." }], "latency_ms": 123 }`
- `GET /api/v1/technologies` (indexed technologies + chunk counts)

Additional endpoints (sources/ingestion management):

- `GET /api/v1/sources`
- `POST /api/v1/sources`
- `DELETE /api/v1/sources/{technology}/{url_id}`
- `POST /api/v1/ingest`

---

## Project structure

```
DocuRAG/
  config/
    config.yaml
    sources.yaml
    ag2_config.yaml

  src/
    api/
      app.py                 # FastAPI wrapper for the React UI
    agents/
      smart_retriever.py     # smart_search multi-tech routing
      assistant_agent.py     # AG2 runner (experimental)
    generation/
      chain.py               # RAG chain + technology-scoped retrieval
    ingestion/
      scraper.py             # scraping + cleanup (e.g. removes header anchor artifacts like "¶")
      pipeline.py            # chunking/embedding/upsert + stats
      sources_manager.py     # runtime sources management
    ui/
      streamlit_app.py       # legacy UI

  frontend/                  # React UI (Vite)
    src/
    package.json

  scripts/
    ingest.py
    test_rag.py
    inspect_chunks.py
```

---

## How it works (high level)

### Ingestion pipeline

1. Scrape pages from configured official docs URLs.
2. Remove navigation noise and header anchor artifacts.
3. Chunk the cleaned text.
4. Embed chunks (Ollama embeddings) and upsert into ChromaDB.

### Retrieval + generation

- The retriever uses MMR to balance relevance and diversity.
- The answer is generated only from retrieved context.
- Sources are returned as structured metadata and displayed in the UI.

---

## Known limitations

- **JavaScript-rendered docs**: sites that require JS execution are not supported (BeautifulSoup parses static HTML).
- **First response latency**: local LLM cold-start can take time; subsequent responses are faster.

---

## Roadmap

- PDF / book ingestion in the UI
- More ingestion sources and better crawling controls
- Evaluation harness (quality checks)

