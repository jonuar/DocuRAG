import hashlib
import time
import requests
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from loguru import logger
import yaml

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

def scrape_url(url: str, content_selector: str = "main") -> str:
    """Extrae texto limpio de una URL."""
    headers = {"User-Agent": "Mozilla/5.0 (RAG Educational Bot)"}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Eliminar ruido
        for tag in soup(["nav", "footer", "script", "style", "aside"]):
            tag.decompose()

        content = soup.select_one(content_selector) or soup.find("body")
        return content.get_text(separator="\n", strip=True) if content else ""
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return ""

def ingest_urls(urls: list[str], technology: str, content_selector: str = "main") -> dict:
    """
    Ingesta una lista de URLs en ChromaDB.
    Retorna stats de la ingesta.
    """
    total_chunks = 0
    errors = []

    for url in urls:
        logger.info(f"Ingesting: {url}")
        text = scrape_url(url, content_selector)

        if not text or len(text) < 100:
            logger.warning(f"Skipping {url} — content too short or empty")
            errors.append(url)
            continue

        # Detectar sección por el título de la página
        try:
            soup = BeautifulSoup(requests.get(url, timeout=30).text, "html.parser")
            section = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
        except Exception:
            section = ""

        chunks = splitter.split_text(text)
        docs = []

        for i, chunk in enumerate(chunks):
            chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()[:12]
            docs.append(Document(
                page_content=chunk,
                metadata={
                    "source_url": url,
                    "technology": technology,
                    "section": section,
                    "chunk_id": f"{technology}_{chunk_hash}_{i}",
                }
            ))

        # Upsert evitando duplicados por chunk_id
        existing_ids = set(vectorstore.get()["ids"])
        new_docs = [d for d in docs if d.metadata["chunk_id"] not in existing_ids]

        if new_docs:
            vectorstore.add_documents(
                new_docs,
                ids=[d.metadata["chunk_id"] for d in new_docs]
            )
            total_chunks += len(new_docs)
            logger.success(f"Added {len(new_docs)} chunks from {url}")
        else:
            logger.info(f"No new chunks from {url} (already indexed)")

        time.sleep(1.5)  # Rate limiting

    return {"chunks_ingested": total_chunks, "errors": errors, "urls_processed": len(urls)}