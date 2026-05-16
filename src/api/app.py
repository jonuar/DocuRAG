import time
from typing import Literal

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.generation.chain import query as rag_query
from src.ingestion.pipeline import get_stats


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    technology: str | None = None
    mode: Literal["rag", "agent"] = "rag"


class SourceItem(BaseModel):
    url: str
    technology: str = ""
    section: str = ""


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem] = []
    latency_ms: int


app = FastAPI(title="DocuRAG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/technologies")
def technologies():
    with open("config/sources.yaml") as f:
        sources_cfg = yaml.safe_load(f)
    stats = get_stats()

    techs = []
    for key, cfg in sources_cfg.get("technologies", {}).items():
        techs.append(
            {
                "key": key,
                "name": cfg.get("name", key),
                "chunks": int(stats["by_technology"].get(key, 0)),
            }
        )

    return {"technologies": techs, "total_chunks": int(stats["total_chunks"])}


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    start = time.time()

    if req.mode == "agent":
        from src.agents.assistant_agent import run_agent

        agent_question = (
            f"Tecnología preferida: {req.technology or ''}\n\nPregunta: {req.message}"
        )
        answer = run_agent(agent_question)
        sources = []
    else:
        result = rag_query(req.message, technology=req.technology)
        answer = result["answer"]
        sources = result["sources"]

    latency_ms = int((time.time() - start) * 1000)
    return {"answer": answer, "sources": sources, "latency_ms": latency_ms}

