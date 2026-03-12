import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.pipeline import ingest_urls
from loguru import logger
import yaml

with open("config/sources.yaml") as f:
    sources = yaml.safe_load(f)

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/ingest.py <technology>")
        print(f"Tecnologías disponibles: {list(sources['technologies'].keys())}")
        sys.exit(1)

    technology = sys.argv[1]

    if technology not in sources["technologies"]:
        print(f"Tecnología '{technology}' no encontrada en sources.yaml")
        sys.exit(1)

    tech_config = sources["technologies"][technology]
    urls = tech_config["docs_urls"]
    selector = tech_config.get("selectors", {}).get("content", "main")

    logger.info(f"Starting ingestion for: {technology} ({len(urls)} URLs)")
    result = ingest_urls(urls=urls, technology=technology, content_selector=selector)

    print(f"\n✅ Ingesta completada:")
    print(f"   Chunks ingresados: {result['chunks_ingested']}")
    print(f"   URLs procesadas: {result['pages_processed']}")
    if result["errors"]:
        print(f"   Errores en: {result['errors']}")

if __name__ == "__main__":
    main()