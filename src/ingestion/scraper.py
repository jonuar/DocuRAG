import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from loguru import logger
import re


def _clean_text(text: str) -> str:
    """Limpia texto extraído de HTML."""
    # Artefactos de encoding
    text = (text
            .replace("Â¶", "")
            .replace("Â", "")
            .replace("¶", "")
            .replace("â¦", "…")
            .replace("â\x80\x93", "–")
            .replace("â\x80\x94", "—"))

    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if _is_noise_line(stripped):
            continue
        lines.append(stripped)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_noise_line(stripped: str) -> bool:
    """
    Versión conservadora: solo elimina líneas que son
    EXCLUSIVAMENTE prompts de consola Python aislados.
    No elimina operadores que pueden formar parte de frases.
    """
    if not stripped:
        return False

    # Solo eliminar prompts de consola puros, nunca operadores
    pure_noise = {">>>", "..."}
    return stripped in pure_noise



def _extract_code_blocks(soup: BeautifulSoup) -> None:
    """
    Reemplaza bloques de código fragmentados por texto plano.
    Python docs usa divs con clase 'highlight' que contienen
    spans individuales por token — esto los colapsa en texto limpio.
    """
    selectors = [
        "div.highlight",
        "div.highlight-python3",
        "div.highlight-default",
        "div.highlight-pycon",
        "pre.literal-block",
        "pre.doctest",
    ]
    for selector in selectors:
        for block in soup.select(selector):
            # get_text sin separador colapsa los spans en texto continuo
            code_text = block.get_text(separator="")
            new_tag = soup.new_tag("pre")
            new_tag.string = "\n" + code_text.strip() + "\n"
            block.replace_with(new_tag)


class DocScraper:

    def __init__(self, delay: float = 1.5, timeout: int = 30, max_pages: int = 50):
        self.delay = delay
        self.timeout = timeout
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (RAG Educational Bot)"
        })

    def _is_same_domain(self, url: str, base_url: str) -> bool:
        return urlparse(url).netloc == urlparse(base_url).netloc

    def _is_doc_link(self, url: str, base_path: str) -> bool:
        parsed = urlparse(url)
        if parsed.fragment and not parsed.path:
            return False
        if any(url.endswith(ext) for ext in [".png", ".jpg", ".pdf", ".zip", ".gz"]):
            return False
        return parsed.path.startswith(urlparse(base_path).path)

    def scrape_page(self, url: str, content_selector: str = "main") -> dict:
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Decodificar desde bytes con detección automática
            # Esto evita que requests asuma Latin-1 en páginas sin charset
            raw_bytes = response.content
            try:
                text_html = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text_html = raw_bytes.decode("latin-1")

            soup = BeautifulSoup(text_html, "html.parser")

            # Título antes de eliminar nada
            title = ""
            h1 = soup.find("h1")
            if h1:
                # Eliminar el ¶ del título antes de extraer texto
                for a in h1.find_all("a", class_="headerlink"):
                    a.decompose()
                title = h1.get_text(strip=True)
            elif soup.find("title"):
                title = soup.find("title").get_text(strip=True)

            # 1. Colapsar bloques de código ANTES de eliminar nada
            _extract_code_blocks(soup)

            # 2. Eliminar ruido navegacional
            for tag in soup.select(
                "nav, footer, script, style, aside, "
                "a.headerlink, .sphinxsidebar, .related, "
                ".navigation, #searchbox, dt"
            ):
                tag.decompose()

            # 3. Extraer contenido principal
            content = soup.select_one(content_selector)
            if not content:
                content = soup.find("body")

            raw_text = content.get_text(separator="\n") if content else ""

            # 4. Limpiar texto
            clean = _clean_text(raw_text)

            # Links internos para crawling
            links = []
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"]).split("#")[0]
                if href and href != url:
                    links.append(href)

            return {
                "url": url,
                "title": title,
                "text": clean,
                "links": list(set(links)),
                "success": bool(clean),
            }

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {"url": url, "title": "", "text": "", "links": [], "success": False}

    def crawl(self, start_url: str, content_selector: str = "main") -> list[dict]:
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
                for link in page["links"]:
                    if (link not in visited
                            and self._is_same_domain(link, start_url)
                            and self._is_doc_link(link, start_url)):
                        queue.append(link)

            time.sleep(self.delay)

        logger.success(f"Crawl complete: {len(results)} pages from {start_url}")
        return results