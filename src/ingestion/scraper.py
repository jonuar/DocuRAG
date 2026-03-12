import time
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from loguru import logger


class DocScraper:
    """
    Scraper que sigue links internos de una documentación
    hasta una profundidad máxima configurable.
    """

    def __init__(self, delay: float = 1.5, timeout: int = 30, max_pages: int = 50):
        self.delay = delay
        self.timeout = timeout
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (RAG Educational Bot)"})

    def _is_same_domain(self, url: str, base_url: str) -> bool:
        return urlparse(url).netloc == urlparse(base_url).netloc

    def _is_doc_link(self, url: str, base_path: str) -> bool:
        """Filtra solo links que sean parte de la documentación."""
        parsed = urlparse(url)
        # Excluir anchors, archivos, y links externos
        if parsed.fragment and not parsed.path:
            return False
        if any(url.endswith(ext) for ext in [".png", ".jpg", ".pdf", ".zip", ".gz"]):
            return False
        # El path debe empezar igual que la URL base
        return parsed.path.startswith(urlparse(base_path).path)

    def scrape_page(self, url: str, content_selector: str = "main") -> dict:
        """Extrae texto y metadata de una página."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Título
            title = ""
            if soup.find("h1"):
                title = soup.find("h1").get_text(strip=True)
            elif soup.find("title"):
                title = soup.find("title").get_text(strip=True)

            # Eliminar ruido navegacional
            for tag in soup(
                [
                    "nav",
                    "footer",
                    "script",
                    "style",
                    "aside",
                    ".sidebar",
                    "#sidebar",
                    ".toc",
                    ".navigation",
                ]
            ):
                tag.decompose()

            # Extraer contenido principal
            content = soup.select_one(content_selector)
            if not content:
                content = soup.find("body")

            text = content.get_text(separator="\n", strip=True) if content else ""

            # Extraer links internos para crawling
            links = []
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"])
                # Limpiar anchors del final
                href = href.split("#")[0]
                if href and href != url:
                    links.append(href)

            return {
                "url": url,
                "title": title,
                "text": text,
                "links": list(set(links)),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {"url": url, "title": "", "text": "", "links": [], "success": False}

    def crawl(self, start_url: str, content_selector: str = "main") -> list[dict]:
        """
        Crawlea una sección de documentación siguiendo links internos.
        Empieza en start_url y sigue solo links del mismo dominio y path.
        """
        visited = set()
        queue = [start_url]
        results = []

        while queue and len(visited) < self.max_pages:
            url = queue.pop(0)

            if url in visited:
                continue

            visited.add(url)
            logger.info(f"Crawling ({len(visited)}/{self.max_pages}): {url}")

            page = self.scrape_page(url, content_selector)

            if page["success"] and len(page["text"]) > 200:
                results.append(page)

                # Añadir links internos válidos a la cola
                for link in page["links"]:
                    if (
                        link not in visited
                        and self._is_same_domain(link, start_url)
                        and self._is_doc_link(link, start_url)
                    ):
                        queue.append(link)

            time.sleep(self.delay)

        logger.success(f"Crawl complete: {len(results)} pages from {start_url}")
        return results
