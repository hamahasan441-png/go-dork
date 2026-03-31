"""Core dorking/search engine scraping logic."""

import re
import logging
from urllib.parse import quote_plus, unquote, urlparse

import requests

REQUEST_TIMEOUT = 15

logger = logging.getLogger(__name__)

# Search engine configurations: (base_url, regex_pattern, page_param_builder)
ENGINES = {
    "google": {
        "base_url": "https://www.google.com/search",
        "pattern": r'"><a href="\/url\?q=(.*?)&amp;sa=U&amp;',
        "build_params": lambda query, page: {"q": query, "start": str(page * 10)},
        "supports_pagination": True,
    },
    "shodan": {
        "base_url": "https://www.shodan.io/search",
        "pattern": r'"><a href="/host/(.*?)">',
        "build_params": lambda query, page: {"query": query, "page": str(page + 1)},
        "supports_pagination": True,
    },
    "bing": {
        "base_url": "https://www.bing.com/search",
        "pattern": r'</li><li class="b_algo"><h2><a href="(.*?)" h="ID=SERP,',
        "build_params": lambda query, page: {"q": query, "first": str(page * 10 + 1)},
        "supports_pagination": True,
    },
    "duck": {
        "base_url": "https://html.duckduckgo.com/html/",
        "pattern": (
            r'<a rel="nofollow" href="//duckduckgo.com/l/\?kh=-1&amp;uddg=(.*?)">'
        ),
        "build_params": lambda query, page: {"q": query},
        "supports_pagination": False,
    },
    "yahoo": {
        "base_url": "https://search.yahoo.com/search",
        "pattern": (
            r'" ac-algo fz-l ac-21th lh-24" href="(.*?)" referrerpolicy="origin'
        ),
        "build_params": lambda query, page: {"p": query, "b": str(page * 10 + 1)},
        "supports_pagination": True,
    },
    "ask": {
        "base_url": "https://www.ask.com/web",
        "pattern": r"target=\"_blank\" href='(.*?)' data-unified=",
        "build_params": lambda query, page: {"q": query, "page": str(page + 1)},
        "supports_pagination": True,
    },
}


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
) -> str:
    """Make an HTTP GET request and return the response text."""
    req_headers = {"User-Agent": "Mozilla/5.0"}
    if headers:
        req_headers.update(headers)

    proxies = None
    if proxy:
        proxies = {"http": proxy, "https": proxy}
        req_headers["Connection"] = "close"

    try:
        resp = requests.get(
            url,
            params=params,
            headers=req_headers,
            proxies=proxies,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        logger.error("Request failed: %s", exc)
        return ""


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

    for page in range(max_pages):
        params = cfg["build_params"](query, page)
        html = _make_request(cfg["base_url"], params, proxy=proxy, headers=headers)
        if not html:
            break

        matches = re.findall(cfg["pattern"], html)
        if not matches:
            break

        for match in matches:
            url = unquote(match)
            if not _is_valid_url(url):
                continue
            if url not in seen:
                seen.add(url)
                results.append(url)

    return results
