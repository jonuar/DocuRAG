import yaml
from pathlib import Path
from loguru import logger

SOURCES_FILE = Path("config/sources.yaml")


def load_sources() -> dict:
    """Carga la configuración actual de sources."""
    if not SOURCES_FILE.exists():
        return {"technologies": {}}
    
    with open(SOURCES_FILE) as f:
        return yaml.safe_load(f) or {"technologies": {}}


def save_sources(data: dict) -> None:
    """Guarda la configuración de sources."""
    with open(SOURCES_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    logger.info(f"Sources saved to {SOURCES_FILE}")


def add_source(technology: str, name: str, url: str, selectors: dict = None) -> dict:
    """
    Agrega una nueva URL de documentación.
    
    Args:
        technology: slug (ej: 'fastapi', 'python')
        name: nombre legible (ej: 'FastAPI')
        url: URL de la documentación
        selectors: dict con selectores CSS {content: "article"}
    
    Returns:
        Config actualizada
    """
    sources = load_sources()
    
    if technology not in sources["technologies"]:
        sources["technologies"][technology] = {
            "name": name,
            "docs_urls": [],
            "selectors": selectors or {"content": "article"}
        }
    
    # Agregar URL si no existe
    if url not in sources["technologies"][technology]["docs_urls"]:
        sources["technologies"][technology]["docs_urls"].append(url)
        logger.info(f"Added URL to {technology}: {url}")
    
    save_sources(sources)
    return sources


def remove_source(technology: str, url: str) -> dict:
    """Elimina una URL de documentación."""
    sources = load_sources()
    
    if technology in sources["technologies"]:
        if url in sources["technologies"][technology]["docs_urls"]:
            sources["technologies"][technology]["docs_urls"].remove(url)
            logger.info(f"Removed URL from {technology}: {url}")
    
    save_sources(sources)
    return sources


def list_sources() -> dict:
    """Retorna todas las fuentes configuradas."""
    return load_sources()


def clear_technology(technology: str) -> dict:
    """Elimina todas las URLs de una tecnología."""
    sources = load_sources()
    
    if technology in sources["technologies"]:
        del sources["technologies"][technology]
        logger.info(f"Cleared all sources for {technology}")
    
    save_sources(sources)
    return sources
