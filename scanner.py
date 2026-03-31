"""Vulnerability scanner for testing URLs for SQLi, XSS, and LFI/RFI."""

import logging
import re
import time
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# --- SQLi Detection ---

SQLI_PAYLOADS = [
    "'",
    '"',
    "' OR '1'='1",
    "1' OR '1'='1' --",
    "1 OR 1=1",
    "' UNION SELECT NULL--",
    "1' AND '1'='1",
]

SQLI_ERROR_PATTERNS = [
    re.compile(r"you have an error in your sql syntax", re.I),
    re.compile(r"warning:.*mysql_", re.I),
    re.compile(r"unclosed quotation mark", re.I),
    re.compile(r"quoted string not properly terminated", re.I),
    re.compile(r"microsoft ole db provider for odbc drivers", re.I),
    re.compile(r"microsoft ole db provider for sql server", re.I),
    re.compile(r"incorrect syntax near", re.I),
    re.compile(r"pg_query\(\).*error", re.I),
    re.compile(r"pg_exec\(\).*error", re.I),
    re.compile(r"valid postgresql result", re.I),
    re.compile(r"syntax error at or near", re.I),
    re.compile(r"unterminated.*string", re.I),
    re.compile(r"SQL command not properly ended", re.I),
    re.compile(r"ORA-\d{4,5}", re.I),
    re.compile(r"SQLite3?::SQLException", re.I),
    re.compile(r"SQLITE_ERROR", re.I),
    re.compile(r"MySQL server version for the right syntax", re.I),
    re.compile(r"mysql_fetch", re.I),
    re.compile(r"mysqli_", re.I),
    re.compile(r"supplied argument is not a valid MySQL", re.I),
]

# --- XSS Detection ---

# We use a unique marker to detect reflection
XSS_MARKER = "d0rk5c4n"
XSS_PAYLOADS = [
    f"<script>{XSS_MARKER}</script>",
    f'"><img src=x onerror={XSS_MARKER}>',
    f"'><svg onload={XSS_MARKER}>",
    f"{XSS_MARKER}",
    f'"><{XSS_MARKER}>',
    f"javascript:{XSS_MARKER}",
]

# --- LFI/RFI Detection ---

LFI_PAYLOADS = [
    "../../../../../../etc/passwd",
    "..\\..\\..\\..\\..\\..\\windows\\win.ini",
    "....//....//....//....//....//etc/passwd",
    "/etc/passwd",
    "....//....//....//etc/passwd%00",
    "php://filter/convert.base64-encode/resource=index.php",
    "/proc/self/environ",
]

LFI_SUCCESS_PATTERNS = [
    re.compile(r"root:.*:0:0:", re.I),  # /etc/passwd
    re.compile(r"\[extensions\]", re.I),  # win.ini
    re.compile(r"\[fonts\]", re.I),  # win.ini
    re.compile(r"for 16-bit app support", re.I),  # win.ini
    re.compile(r"DOCUMENT_ROOT=", re.I),  # /proc/self/environ
    re.compile(r"HTTP_USER_AGENT=", re.I),  # /proc/self/environ
]


def _fetch(url: str, proxy: str = "") -> str:
    """Fetch a URL and return response text."""
    headers = {"User-Agent": _USER_AGENT}
    proxies = None
    if proxy:
        proxies = {"http": proxy, "https": proxy}
        headers["Connection"] = "close"

    try:
        resp = requests.get(
            url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )
        return resp.text
    except requests.RequestException as exc:
        logger.error("Scanner request failed for %s: %s", url, exc)
        return ""


def _inject_param(url: str, param: str, payload: str) -> str:
    """Replace a query parameter's value with the given payload."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params[param] = [payload]
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _get_params(url: str) -> list[str]:
    """Extract query parameter names from a URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    return list(params.keys())


def test_sqli(url: str, proxy: str = "") -> list[dict]:
    """
    Test a URL for SQL injection vulnerabilities.

    Returns a list of findings, each a dict with:
        - url: the injected URL
        - param: the parameter tested
        - payload: the payload used
        - evidence: the error pattern matched
        - severity: 'high'
    """
    findings = []
    params = _get_params(url)
    if not params:
        return findings

    for param in params:
        found = False
        for payload in SQLI_PAYLOADS:
            if found:
                break
            injected_url = _inject_param(url, param, payload)
            body = _fetch(injected_url, proxy=proxy)
            if not body:
                continue

            for pattern in SQLI_ERROR_PATTERNS:
                if pattern.search(body):
                    findings.append({
                        "type": "SQLi",
                        "url": injected_url,
                        "param": param,
                        "payload": payload,
                        "evidence": pattern.pattern,
                        "severity": "high",
                    })
                    found = True
                    break

    return findings


def test_xss(url: str, proxy: str = "") -> list[dict]:
    """
    Test a URL for reflected XSS vulnerabilities.

    Returns a list of findings.
    """
    findings = []
    params = _get_params(url)
    if not params:
        return findings

    for param in params:
        for payload in XSS_PAYLOADS:
            injected_url = _inject_param(url, param, payload)
            body = _fetch(injected_url, proxy=proxy)
            if not body:
                continue

            # Check if our marker is reflected in the response, then verify
            # whether the full payload (with HTML tags) appears unescaped
            if XSS_MARKER in body:
                reflected_raw = payload in body
                findings.append({
                    "type": "XSS",
                    "url": injected_url,
                    "param": param,
                    "payload": payload,
                    "evidence": (
                        "Full payload reflected in response"
                        if reflected_raw
                        else "Marker reflected in response"
                    ),
                    "severity": "high" if reflected_raw else "medium",
                })
                break  # Found reflection for this param

    return findings


def test_lfi(url: str, proxy: str = "") -> list[dict]:
    """
    Test a URL for Local File Inclusion vulnerabilities.

    Returns a list of findings.
    """
    findings = []
    params = _get_params(url)
    if not params:
        return findings

    for param in params:
        found = False
        for payload in LFI_PAYLOADS:
            if found:
                break
            injected_url = _inject_param(url, param, payload)
            body = _fetch(injected_url, proxy=proxy)
            if not body:
                continue

            for pattern in LFI_SUCCESS_PATTERNS:
                if pattern.search(body):
                    findings.append({
                        "type": "LFI",
                        "url": injected_url,
                        "param": param,
                        "payload": payload,
                        "evidence": pattern.pattern,
                        "severity": "critical",
                    })
                    found = True
                    break

    return findings


def scan_url(url: str, proxy: str = "") -> list[dict]:
    """
    Run all vulnerability tests on a single URL.

    Returns a combined list of all findings.
    """
    findings = []
    findings.extend(test_sqli(url, proxy=proxy))
    findings.extend(test_xss(url, proxy=proxy))
    findings.extend(test_lfi(url, proxy=proxy))
    return findings


def scan_urls(urls: list[str], proxy: str = "") -> list[dict]:
    """
    Scan multiple URLs for vulnerabilities.

    Returns a combined list of all findings across all URLs.
    """
    all_findings = []
    for url in urls:
        try:
            results = scan_url(url, proxy=proxy)
            all_findings.extend(results)
        except Exception as exc:
            logger.error("Error scanning %s: %s", url, exc)
    return all_findings
