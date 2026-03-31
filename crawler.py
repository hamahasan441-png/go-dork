"""URL crawler that collects links and parameterized URLs from target pages."""

import logging
import re
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Maximum number of URLs to crawl from a single target to avoid runaway crawling
MAX_CRAWL_URLS = 200


def _fetch(url: str, proxy: str = "") -> str:
    """Fetch a URL and return the response text."""
    headers = {"User-Agent": _USER_AGENT}
    proxies = None
    if proxy:
        proxies = {"http": proxy, "https": proxy}
        headers["Connection"] = "close"

    try:
        resp = requests.get(
            url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        logger.error("Crawler request failed for %s: %s", url, exc)
        return ""


def _same_domain(url: str, base_domain: str) -> bool:
    """Check if a URL belongs to the same domain as the base."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().split(":")[0]
        return host == base_domain or host.endswith(f".{base_domain}")
    except Exception:
        return False


def _has_params(url: str) -> bool:
    """Check if a URL has query parameters."""
    try:
        parsed = urlparse(url)
        return bool(parsed.query)
    except Exception:
        return False


def _extract_form_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract action URLs from HTML forms."""
    urls = []
    for form in soup.find_all("form"):
        action = form.get("action", "")
        if action:
            full = urljoin(base_url, action)
            urls.append(full)
    return urls


def crawl(
    target_url: str,
    depth: int = 2,
    proxy: str = "",
) -> dict:
    """
    Crawl a target URL and collect links.

    Args:
        target_url: The starting URL to crawl.
        depth: How many levels deep to crawl (1 = only the target page).
        proxy: Optional proxy URL.

    Returns:
        A dict with keys:
            - all_urls: list of all discovered URLs
            - param_urls: list of URLs that have query parameters
            - form_urls: list of form action URLs found
            - external_urls: list of URLs on different domains
    """
    parsed_base = urlparse(target_url)
    base_domain = parsed_base.netloc.lower().split(":")[0]

    visited: set[str] = set()
    all_urls: list[str] = []
    param_urls: list[str] = []
    form_urls: list[str] = []
    external_urls: list[str] = []

    queue: list[tuple[str, int]] = [(target_url, 0)]
    queued: set[str] = {target_url}

    while queue and len(visited) < MAX_CRAWL_URLS:
        current_url, current_depth = queue.pop(0)

        # Normalize URL (remove fragment)
        parsed = urlparse(current_url)
        normalized = parsed._replace(fragment="").geturl()

        if normalized in visited:
            continue
        visited.add(normalized)

        html = _fetch(current_url, proxy=proxy)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")

        # Extract links from <a> tags
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            full_url = urljoin(current_url, href)
            full_parsed = urlparse(full_url)

            # Only keep http/https
            if full_parsed.scheme not in ("http", "https"):
                continue

            # Remove fragment
            clean_url = full_parsed._replace(fragment="").geturl()

            if clean_url not in visited and clean_url not in queued:
                if _same_domain(clean_url, base_domain):
                    if clean_url not in all_urls:
                        all_urls.append(clean_url)
                    if _has_params(clean_url) and clean_url not in param_urls:
                        param_urls.append(clean_url)
                    if current_depth + 1 < depth:
                        queue.append((clean_url, current_depth + 1))
                        queued.add(clean_url)
                else:
                    if clean_url not in external_urls:
                        external_urls.append(clean_url)

        # Extract form action URLs
        for form_url in _extract_form_urls(soup, current_url):
            if form_url not in form_urls:
                form_urls.append(form_url)

        # Extract URLs from script src attributes
        for script in soup.find_all("script", src=True):
            src = urljoin(current_url, script["src"])
            src_parsed = urlparse(src)
            if src_parsed.scheme in ("http", "https"):
                clean = src_parsed._replace(fragment="").geturl()
                if clean not in all_urls:
                    all_urls.append(clean)

    return {
        "all_urls": all_urls,
        "param_urls": param_urls,
        "form_urls": form_urls,
        "external_urls": external_urls,
    }
