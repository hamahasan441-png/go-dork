"""URL crawler that collects links and parameterized URLs from target pages."""

import logging
import os
import re
import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from urlvalidation import is_safe_url

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = int(os.environ.get("GODORK_REQUEST_TIMEOUT", "15"))
MAX_RETRIES = int(os.environ.get("GODORK_MAX_RETRIES", "3"))
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Maximum number of URLs to crawl from a single target to avoid runaway crawling
MAX_CRAWL_URLS = int(os.environ.get("GODORK_MAX_CRAWL_URLS", "200"))


def _fetch(url: str, proxy: str = "") -> str:
    """Fetch a URL with retry logic and return the response text.

    Validates the URL against internal/private network ranges to prevent SSRF.
    """
    if not is_safe_url(url):
        logger.warning("Blocked request to potentially unsafe URL: %s", url)
        return ""

    headers = {"User-Agent": _USER_AGENT}
    proxies = None
    if proxy:
        proxies = {"http": proxy, "https": proxy}
        headers["Connection"] = "close"

    last_exc = None
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            backoff = 2 ** attempt
            logger.info("Crawler retry %d/%d after %ds for %s", attempt, MAX_RETRIES - 1, backoff, url)
            time.sleep(backoff)

        try:
            resp = requests.get(
                url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            logger.error("Crawler request failed for %s (attempt %d): %s", url, attempt + 1, exc)
            last_exc = exc

    logger.error("All %d crawler attempts failed for %s: %s", MAX_RETRIES, url, last_exc)
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


def _parse_robots_txt(robots_text: str, base_url: str) -> urllib.robotparser.RobotFileParser:
    """Parse robots.txt content and return a RobotFileParser instance."""
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{base_url}/robots.txt")
    rp.parse(robots_text.splitlines())
    return rp


def _extract_sitemap_urls_from_robots(robots_text: str) -> list[str]:
    """Extract Sitemap URLs declared in robots.txt."""
    urls = []
    for line in robots_text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("sitemap:"):
            url = stripped.split(":", 1)[1].strip()
            if url:
                urls.append(url)
    return urls


def _parse_sitemap(sitemap_text: str) -> list[str]:
    """Parse sitemap XML and extract URLs from <loc> tags."""
    if not sitemap_text:
        return []
    soup = BeautifulSoup(sitemap_text, "html.parser")
    urls = []
    for loc in soup.find_all("loc"):
        url = loc.get_text(strip=True)
        if url:
            urls.append(url)
    return urls


def crawl(
    target_url: str,
    depth: int = 2,
    proxy: str = "",
    respect_robots: bool = False,
    use_sitemap: bool = False,
) -> dict:
    """
    Crawl a target URL and collect links.

    Args:
        target_url: The starting URL to crawl.
        depth: How many levels deep to crawl (1 = only the target page).
        proxy: Optional proxy URL.
        respect_robots: When True, fetch and honor the site's robots.txt.
        use_sitemap: When True, discover extra URLs from sitemap.xml.

    Returns:
        A dict with keys:
            - all_urls: list of all discovered URLs
            - param_urls: list of URLs that have query parameters
            - form_urls: list of form action URLs found
            - external_urls: list of URLs on different domains
    """
    parsed_base = urlparse(target_url)
    base_domain = parsed_base.netloc.lower().split(":")[0]
    base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

    visited: set[str] = set()
    all_urls: list[str] = []
    param_urls: list[str] = []
    form_urls: list[str] = []
    external_urls: list[str] = []

    queue: list[tuple[str, int]] = [(target_url, 0)]
    queued: set[str] = {target_url}

    robot_parser: urllib.robotparser.RobotFileParser | None = None

    # --- Pre-crawl: robots.txt and sitemap handling ---
    if respect_robots or use_sitemap:
        robots_url = f"{base_origin}/robots.txt"
        robots_text = _fetch(robots_url, proxy=proxy)

        if respect_robots and robots_text:
            robot_parser = _parse_robots_txt(robots_text, base_origin)

        if use_sitemap:
            sitemap_locations: list[str] = [f"{base_origin}/sitemap.xml"]
            if robots_text:
                for smap_url in _extract_sitemap_urls_from_robots(robots_text):
                    if smap_url not in sitemap_locations:
                        sitemap_locations.append(smap_url)

            for sitemap_url in sitemap_locations:
                sitemap_text = _fetch(sitemap_url, proxy=proxy)
                for url in _parse_sitemap(sitemap_text):
                    url_parsed = urlparse(url)
                    clean_url = url_parsed._replace(fragment="").geturl()
                    if clean_url in queued:
                        continue
                    if robot_parser and not robot_parser.can_fetch(_USER_AGENT, clean_url):
                        continue
                    if _same_domain(clean_url, base_domain):
                        if clean_url not in all_urls:
                            all_urls.append(clean_url)
                        if _has_params(clean_url) and clean_url not in param_urls:
                            param_urls.append(clean_url)
                        queue.append((clean_url, 0))
                        queued.add(clean_url)

    while queue and len(visited) < MAX_CRAWL_URLS:
        current_url, current_depth = queue.pop(0)

        # Normalize URL (remove fragment)
        parsed = urlparse(current_url)
        normalized = parsed._replace(fragment="").geturl()

        if normalized in visited:
            continue

        if robot_parser and not robot_parser.can_fetch(_USER_AGENT, normalized):
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
                if robot_parser and not robot_parser.can_fetch(_USER_AGENT, clean_url):
                    continue
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
