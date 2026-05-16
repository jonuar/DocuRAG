import time
from typing import Literal

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.generation.chain import query as rag_query
from src.ingestion.pipeline import get_stats
from src.ingestion.sources_manager import (
    add_source, remove_source, list_sources, clear_technology
)
from loguru import logger


# ─────────────────────────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────────────────────────

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


class SourceRequest(BaseModel):
    technology: str
    name: str
    url: str
    selector_content: str = "article"


class SourceResponse(BaseModel):
    success: bool
    message: str
    sources: dict


class IngestRequest(BaseModel):
    technology: str
    ingest_now: bool = True


# ─────────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# ENDPOINTS EXISTENTES
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/technologies")
def technologies():
    """Lista tecnologías indexadas con estadísticas."""
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
    """
    Chat endpoint con soporte para:
    - mode="rag": Búsqueda directa (rápido)
    - mode="agent": AG2 con razonamiento automático (completo)
    """
    start = time.time()

    if req.mode == "agent":
        from src.agents.smart_retriever import smart_search
        
        # AG2 decide automáticamente qué búscar
        answer = smart_search(req.message)
        sources = []
    else:
        # RAG directo: si especifica technology, lo usa
        result = rag_query(req.message, technology=req.technology)
        answer = result["answer"]
        sources = result["sources"]

    latency_ms = int((time.time() - start) * 1000)
    final_answer = (answer or "").strip()
    if not final_answer:
        final_answer = "No se pudo generar una respuesta (respuesta vacía)."

    return ChatResponse(
        answer=final_answer,
        sources=sources,
        latency_ms=latency_ms
    )


# ─────────────────────────────────────────────────────────────
# NUEVOS ENDPOINTS: GESTIÓN DE SOURCES
# ─────────────────────────────────────────────────────────────

@app.get("/api/v1/sources")
def get_sources():
    """Obtiene todas las URLs configuradas."""
    sources = list_sources()
    return {"sources": sources.get("technologies", {})}


@app.post("/api/v1/sources", response_model=SourceResponse)
def add_source_endpoint(req: SourceRequest):
    """
    Agrega una nueva URL de documentación dinámicamente.
    
    Ejemplo:
    {
        "technology": "fastapi",
        "name": "FastAPI",
        "url": "https://fastapi.tiangolo.com/tutorial/",
        "selector_content": "article"
    }
    """
    try:
        sources = add_source(
            technology=req.technology.lower(),
            name=req.name,
            url=req.url,
            selectors={"content": req.selector_content}
        )
        return SourceResponse(
            success=True,
            message=f"URL agregada a {req.technology}",
            sources=sources.get("technologies", {})
        )
    except Exception as e:
        logger.error(f"Error adding source: {e}")
        return SourceResponse(
            success=False,
            message=str(e),
            sources={}
        )


@app.delete("/api/v1/sources/{technology}/{url_id}")
def remove_source_endpoint(technology: str, url_id: str):
    """Elimina una URL de documentación."""
    try:
        from urllib.parse import unquote
        url = unquote(url_id)
        
        sources = remove_source(technology, url)
        return {
            "success": True,
            "message": f"URL eliminada de {technology}",
            "sources": sources.get("technologies", {})
        }
    except Exception as e:
        logger.error(f"Error removing source: {e}")
        return {
            "success": False,
            "message": str(e),
            "sources": {}
        }


# ─────────────────────────────────────────────────────────────
# NUEVOS ENDPOINTS: INGESTA
# ─────────────────────────────────────────────────────────────

@app.post("/api/v1/ingest")
def ingest_technology(req: IngestRequest):
    """
    Ingesta documentación de una tecnología.
    
    Si ingest_now=true: ingesta inmediatamente
    Si ingest_now=false: solo valida URLs configuradas
    """
    try:
        if req.ingest_now:
            from src.ingestion.pipeline import run_ingestion
            
            # Ejecutar ingesta
            result = run_ingestion(req.technology)
            
            return {
                "success": True,
                "message": f"Ingesta completada para {req.technology}",
                "chunks_ingested": result.get("chunks_ingested", 0),
                "errors": result.get("errors", [])
            }
        else:
            sources = list_sources()
            tech_sources = sources.get("technologies", {}).get(req.technology, {})
            return {
                "success": True,
                "message": f"URLs configuradas para {req.technology}",
                "urls": tech_sources.get("docs_urls", [])
            }
    
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        return {
            "success": False,
            "message": str(e),
            "chunks_ingested": 0,
            "errors": [str(e)]
        }
