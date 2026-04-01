"""Core dorking/search engine scraping logic using BeautifulSoup."""

import logging
import os
import time
from urllib.parse import unquote, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = int(os.environ.get("GODORK_REQUEST_TIMEOUT", "15"))
MAX_RETRIES = int(os.environ.get("GODORK_MAX_RETRIES", "3"))

logger = logging.getLogger(__name__)

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# BeautifulSoup-based extractor functions (one per search engine)
# ---------------------------------------------------------------------------


def _extract_google(soup: BeautifulSoup) -> list[str]:
    """Extract result URLs from a Google search page."""
    urls: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("/url?"):
            params = parse_qs(urlparse(href).query)
            if "q" in params:
                urls.append(params["q"][0])
    return urls


def _extract_bing(soup: BeautifulSoup) -> list[str]:
    """Extract result URLs from a Bing search page."""
    urls: list[str] = []
    for a_tag in soup.select("li.b_algo h2 a[href]"):
        urls.append(a_tag["href"])
    return urls


def _extract_yahoo(soup: BeautifulSoup) -> list[str]:
    """Extract result URLs from a Yahoo search page."""
    urls: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        classes = a_tag.get("class", [])
        if "ac-algo" in classes:
            urls.append(a_tag["href"])
    # Fallback: broader Yahoo result link selector
    if not urls:
        for a_tag in soup.select("h3.title a[href]"):
            urls.append(a_tag["href"])
    return urls


def _extract_duck(soup: BeautifulSoup) -> list[str]:
    """Extract result URLs from DuckDuckGo HTML search page."""
    urls: list[str] = []
    for a_tag in soup.select("a.result__a[href]"):
        urls.append(a_tag["href"])
    # Fallback: nofollow redirect links with uddg param
    if not urls:
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "uddg=" in href:
                full = "https:" + href if href.startswith("//") else href
                params = parse_qs(urlparse(full).query)
                if "uddg" in params:
                    urls.append(params["uddg"][0])
    return urls


def _extract_shodan(soup: BeautifulSoup) -> list[str]:
    """Extract result IPs/URLs from a Shodan search page."""
    urls: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("/host/"):
            ip = href[len("/host/"):]
            urls.append(f"https://www.shodan.io/host/{ip}")
    return urls


def _extract_ask(soup: BeautifulSoup) -> list[str]:
    """Extract result URLs from an Ask.com search page."""
    urls: list[str] = []
    for a_tag in soup.select("a.PartialSearchResults-item-title-link[href]"):
        urls.append(a_tag["href"])
    # Fallback
    if not urls:
        for a_tag in soup.find_all("a", href=True, target="_blank"):
            href = a_tag["href"]
            if href.startswith("http"):
                urls.append(href)
    return urls


def _extract_startpage(soup: BeautifulSoup) -> list[str]:
    """Extract result URLs from a Startpage search page."""
    urls: list[str] = []
    for a_tag in soup.select("a.w-gl__result-url[href]"):
        urls.append(a_tag["href"])
    # Fallback: broader result link selector
    if not urls:
        for a_tag in soup.select(".w-gl__result a[href]"):
            href = a_tag["href"]
            if href.startswith("http"):
                urls.append(href)
    return urls


def _extract_brave(soup: BeautifulSoup) -> list[str]:
    """Extract result URLs from a Brave Search page."""
    urls: list[str] = []
    for a_tag in soup.select("a.result-header[href]"):
        urls.append(a_tag["href"])
    # Fallback: look for data-href in result snippets
    if not urls:
        for div in soup.select(".snippet[data-pos]"):
            a_tag = div.find("a", href=True)
            if a_tag and a_tag["href"].startswith("http"):
                urls.append(a_tag["href"])
    return urls


# ---------------------------------------------------------------------------
# Engine configurations
# ---------------------------------------------------------------------------

ENGINES = {
    "google": {
        "base_url": "https://www.google.com/search",
        "extract": _extract_google,
        "build_params": lambda query, page: {"q": query, "start": str(page * 10)},
        "supports_pagination": True,
        "method": "GET",
    },
    "shodan": {
        "base_url": "https://www.shodan.io/search",
        "extract": _extract_shodan,
        "build_params": lambda query, page: {"query": query, "page": str(page + 1)},
        "supports_pagination": True,
        "method": "GET",
    },
    "bing": {
        "base_url": "https://www.bing.com/search",
        "extract": _extract_bing,
        "build_params": lambda query, page: {"q": query, "first": str(page * 10 + 1)},
        "supports_pagination": True,
        "method": "GET",
    },
    "duck": {
        "base_url": "https://html.duckduckgo.com/html/",
        "extract": _extract_duck,
        "build_params": lambda query, page: {"q": query},
        "supports_pagination": False,
        "method": "POST",
    },
    "yahoo": {
        "base_url": "https://search.yahoo.com/search",
        "extract": _extract_yahoo,
        "build_params": lambda query, page: {"p": query, "b": str(page * 10 + 1)},
        "supports_pagination": True,
        "method": "GET",
    },
    "ask": {
        "base_url": "https://www.ask.com/web",
        "extract": _extract_ask,
        "build_params": lambda query, page: {"q": query, "page": str(page + 1)},
        "supports_pagination": True,
        "method": "GET",
    },
    "startpage": {
        "base_url": "https://www.startpage.com/sp/search",
        "extract": _extract_startpage,
        "build_params": lambda query, page: {"query": query, "page": str(page + 1)},
        "supports_pagination": True,
        "method": "POST",
    },
    "brave": {
        "base_url": "https://search.brave.com/search",
        "extract": _extract_brave,
        "build_params": lambda query, page: {"q": query, "offset": str(page)},
        "supports_pagination": True,
        "method": "GET",
    },
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL with scheme and host."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _make_request(
    url: str,
    params: dict,
    proxy: str = "",
    headers: dict | None = None,
    method: str = "GET",
    session: requests.Session | None = None,
) -> str:
    """Make an HTTP request with retry logic and return the response text."""
    req_headers = {"User-Agent": _DEFAULT_USER_AGENT}
    if headers:
        req_headers.update(headers)

    proxies = None
    if proxy:
        proxies = {"http": proxy, "https": proxy}
        req_headers["Connection"] = "close"

    http = session or requests

    last_exc = None
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            backoff = 2 ** attempt
            logger.info("Retry %d/%d after %ds for %s", attempt, MAX_RETRIES - 1, backoff, url)
            time.sleep(backoff)

        try:
            if method.upper() == "POST":
                resp = http.post(
                    url,
                    data=params,
                    headers=req_headers,
                    proxies=proxies,
                    timeout=REQUEST_TIMEOUT,
                )
            else:
                resp = http.get(
                    url,
                    params=params,
                    headers=req_headers,
                    proxies=proxies,
                    timeout=REQUEST_TIMEOUT,
                )

            # Detect captcha / rate-limit responses
            if resp.status_code == 429:
                logger.warning("Rate limited (HTTP 429) from %s", url)
                last_exc = requests.HTTPError("Rate limited (HTTP 429)")
                continue

            if resp.status_code == 503:
                body_lower = resp.text.lower()
                if "captcha" in body_lower or "unusual traffic" in body_lower:
                    logger.warning("Captcha/bot detection triggered at %s", url)
                    last_exc = requests.HTTPError("Captcha/bot detection triggered")
                    continue

            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            logger.error("Request failed (attempt %d): %s", attempt + 1, exc)
            last_exc = exc

    logger.error("All %d attempts failed for %s: %s", MAX_RETRIES, url, last_exc)
    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search(
    query: str,
    engine: str = "google",
    pages: int = 1,
    proxy: str = "",
    headers: dict | None = None,
) -> list[str]:
    """
    Perform a dork search and return a list of result URLs.

    Args:
        query: The search dork query.
        engine: Search engine name (google, shodan, bing, duck, yahoo, ask).
        pages: Number of result pages to scrape.
        proxy: Optional proxy URL (HTTP or SOCKS5).
        headers: Optional dict of custom HTTP headers.

    Returns:
        A list of unique result URLs.

    Raises:
        ValueError: If the engine name is not supported.
    """
    engine = engine.lower().strip()
    if engine not in ENGINES:
        raise ValueError(
            f"Unknown engine '{engine}'. Supported: {', '.join(ENGINES)}"
        )

    cfg = ENGINES[engine]
    results: list[str] = []
    seen: set[str] = set()

    max_pages = 1 if not cfg["supports_pagination"] else max(1, pages)

    # Use a session for connection pooling across pages
    session = requests.Session()
    try:
        for page in range(max_pages):
            params = cfg["build_params"](query, page)
            html = _make_request(
                cfg["base_url"],
                params,
                proxy=proxy,
                headers=headers,
                method=cfg.get("method", "GET"),
                session=session,
            )
            if not html:
                break

            soup = BeautifulSoup(html, "html.parser")
            matches = cfg["extract"](soup)
            if not matches:
                break

            for url in matches:
                url = unquote(url)
                if not _is_valid_url(url):
                    continue
                if url not in seen:
                    seen.add(url)
                    results.append(url)
    finally:
        session.close()

    return results
