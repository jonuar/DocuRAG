import hashlib
import yaml
from loguru import logger
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from src.ingestion.scraper import DocScraper

with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

embeddings = OllamaEmbeddings(
    model=cfg["embeddings"]["model"],
    base_url=cfg["embeddings"]["base_url"],
)

vectorstore = Chroma(
    collection_name=cfg["vectorstore"]["collection_name"],
    embedding_function=embeddings,
    persist_directory=cfg["vectorstore"]["persist_directory"],
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=cfg["splitter"]["chunk_size"],
    chunk_overlap=cfg["splitter"]["chunk_overlap"],
)

scraper = DocScraper(delay=1.5, max_pages=50)


def _build_documents(pages: list[dict], technology: str) -> list[Document]:
    """Convierte páginas scrapeadas en Documents con metadatos."""
    docs = []
    for page in pages:
        chunks = splitter.split_text(page["text"])
        for i, chunk in enumerate(chunks):
            chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()[:12]
            docs.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "source_url": page["url"],
                        "technology": technology,
                        "section": page["title"],
                        "chunk_id": f"{technology}_{chunk_hash}_{i}",
                    },
                )
            )
    return docs


def _upsert_documents(docs: list[Document]) -> int:
    """Inserta solo documentos nuevos. Retorna cantidad insertada."""
    existing_ids = set(vectorstore.get()["ids"])
    new_docs = [d for d in docs if d.metadata["chunk_id"] not in existing_ids]

    if new_docs:
        vectorstore.add_documents(
            new_docs, ids=[d.metadata["chunk_id"] for d in new_docs]
        )

    return len(new_docs)


def ingest_urls(
    urls: list[str], technology: str, content_selector: str = "main"
) -> dict:
    """Ingesta una lista de URLs específicas (sin crawling)."""
    all_pages = []
    for url in urls:
        page = scraper.scrape_page(url, content_selector)
        if page["success"]:
            all_pages.append(page)

    docs = _build_documents(all_pages, technology)
    chunks_added = _upsert_documents(docs)

    logger.success(f"Ingested {chunks_added} new chunks for '{technology}'")
    return {
        "chunks_ingested": chunks_added,
        "pages_processed": len(all_pages),
        "errors": [p["url"] for p in all_pages if not p["success"]],
    }


def ingest_crawl(
    start_url: str, technology: str, content_selector: str = "main", max_pages: int = 30
) -> dict:
    """Ingesta una sección completa de docs siguiendo links automáticamente."""
    scraper.max_pages = max_pages
    pages = scraper.crawl(start_url, content_selector)
    docs = _build_documents(pages, technology)
    chunks_added = _upsert_documents(docs)

    logger.success(f"Crawl ingested {chunks_added} new chunks for '{technology}'")
    return {
        "chunks_ingested": chunks_added,
        "pages_crawled": len(pages),
    }


def get_stats() -> dict:
    """Retorna estadísticas del vectorstore actual."""
    data = vectorstore.get()
    technologies = {}
    for meta in data["metadatas"]:
        tech = meta.get("technology", "unknown")
        technologies[tech] = technologies.get(tech, 0) + 1
    return {"total_chunks": len(data["ids"]), "by_technology": technologies}
