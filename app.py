"""Flask web application for go-dork search engine dorking tool."""

import logging
import os
import re
from urllib.parse import urlparse

from flask import Flask, render_template, request

from dorker import ENGINES, search
from dorkmaker import OPERATORS, TEMPLATES, build_query
from crawler import crawl
from scanner import scan_urls, test_sqli, test_xss, test_lfi
from urlvalidation import is_safe_url

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regex to validate HTTP header names (RFC 7230 token characters)
_VALID_HEADER_NAME = re.compile(r"^[A-Za-z0-9!#$%&'*+\-.^_`|~]+$")
# Reject control characters in header values
_INVALID_HEADER_VALUE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# ---------------------------------------------------------------------------
# Search (original functionality)
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Render the search form."""
    return render_template("index.html", engines=sorted(ENGINES.keys()))


@app.route("/search", methods=["POST"])
def do_search():
    """Handle a search request and display results."""
    query = request.form.get("query", "").strip()
    engine = request.form.get("engine", "google").strip()
    pages = request.form.get("pages", "1").strip()
    proxy = request.form.get("proxy", "").strip()
    raw_headers = request.form.get("headers", "").strip()

    errors = []
    if not query:
        errors.append("Query is required.")

    try:
        pages = int(pages)
        if pages < 1:
            pages = 1
    except ValueError:
        pages = 1

    if engine not in ENGINES:
        errors.append(f"Unknown engine: {engine}")

    if errors:
        return render_template(
            "index.html",
            engines=sorted(ENGINES.keys()),
            errors=errors,
            query=query,
            selected_engine=engine,
            pages=pages,
            proxy=proxy,
            headers=raw_headers,
        )

    # Parse and validate custom headers (one per line, "Name: Value" format)
    custom_headers = {}
    if raw_headers:
        for line in raw_headers.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            if not _VALID_HEADER_NAME.match(key):
                errors.append(f"Invalid header name: {key}")
                continue
            if _INVALID_HEADER_VALUE.search(value):
                errors.append(f"Invalid characters in header value for: {key}")
                continue
            custom_headers[key] = value

    if errors:
        return render_template(
            "index.html",
            engines=sorted(ENGINES.keys()),
            errors=errors,
            query=query,
            selected_engine=engine,
            pages=pages,
            proxy=proxy,
            headers=raw_headers,
        )

    results = search(
        query=query,
        engine=engine,
        pages=pages,
        proxy=proxy,
        headers=custom_headers if custom_headers else None,
    )

    return render_template(
        "index.html",
        engines=sorted(ENGINES.keys()),
        results=results,
        query=query,
        selected_engine=engine,
        pages=pages,
        proxy=proxy,
        headers=raw_headers,
        result_count=len(results),
    )


# ---------------------------------------------------------------------------
# Dork Maker
# ---------------------------------------------------------------------------

@app.route("/dorkmaker", methods=["GET"])
def dorkmaker():
    """Render the dork maker page."""
    return render_template(
        "dorkmaker.html", operators=OPERATORS, templates=TEMPLATES,
    )


@app.route("/dorkmaker/build", methods=["POST"])
def dorkmaker_build():
    """Build a dork query from operator parts."""
    operators_list = request.form.getlist("operator")
    values_list = request.form.getlist("value")

    # Reconstruct parts — negate checkboxes use indexed names (negate_0, negate_1, ...)
    parts = []
    for i in range(len(values_list)):
        op = operators_list[i] if i < len(operators_list) else ""
        val = values_list[i] if i < len(values_list) else ""
        neg = request.form.get(f"negate_{i}") == "1"
        parts.append({"operator": op, "value": val, "negate": neg})

    query = build_query(parts)

    return render_template(
        "dorkmaker.html",
        operators=OPERATORS,
        templates=TEMPLATES,
        query=query,
        parts=parts,
    )


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------

@app.route("/crawler", methods=["GET"])
def crawler_page():
    """Render the crawler page."""
    return render_template("crawler.html")


@app.route("/crawler/crawl", methods=["POST"])
def do_crawl():
    """Handle a crawl request."""
    target_url = request.form.get("target_url", "").strip()
    depth = request.form.get("depth", "2").strip()
    proxy = request.form.get("proxy", "").strip()

    errors = []

    if not target_url:
        errors.append("Target URL is required.")
    else:
        parsed = urlparse(target_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            errors.append("Invalid URL. Must start with http:// or https://")
        elif not is_safe_url(target_url):
            errors.append(
                "URL targets a private or internal network address. "
                "Only public URLs are allowed."
            )

    try:
        depth = int(depth)
        if depth < 1:
            depth = 1
        elif depth > 5:
            depth = 5
    except ValueError:
        depth = 2

    if errors:
        return render_template(
            "crawler.html",
            errors=errors,
            target_url=target_url,
            depth=depth,
            proxy=proxy,
        )

    crawl_results = crawl(target_url=target_url, depth=depth, proxy=proxy)

    return render_template(
        "crawler.html",
        crawl_results=crawl_results,
        target_url=target_url,
        depth=depth,
        proxy=proxy,
    )


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

@app.route("/scanner", methods=["GET"])
def scanner_page():
    """Render the scanner page."""
    return render_template("scanner.html")


@app.route("/scanner/scan", methods=["POST"])
def do_scan():
    """Handle a vulnerability scan request."""
    # URLs can come as a textarea (newline-separated) or as hidden fields
    raw_urls = request.form.get("urls", "")
    url_list = request.form.getlist("urls")
    proxy = request.form.get("proxy", "").strip()
    scan_sqli = request.form.get("scan_sqli") == "1"
    scan_xss = request.form.get("scan_xss") == "1"
    scan_lfi = request.form.get("scan_lfi") == "1"

    # If urls came as a textarea (single string with newlines)
    if len(url_list) == 1 and "\n" in url_list[0]:
        url_list = [u.strip() for u in url_list[0].splitlines() if u.strip()]

    # Default: if no scan types checked via form (e.g. coming from crawler), run all
    if not scan_sqli and not scan_xss and not scan_lfi:
        scan_sqli = scan_xss = scan_lfi = True

    errors = []
    valid_urls = []
    for url in url_list:
        url = url.strip()
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            errors.append(f"Invalid URL skipped: {url}")
            continue
        if not is_safe_url(url):
            errors.append(f"URL targets a private/internal address, skipped: {url}")
            continue
        valid_urls.append(url)

    if not valid_urls:
        errors.append("At least one valid URL with parameters is required.")

    if errors and not valid_urls:
        return render_template(
            "scanner.html",
            errors=errors,
            raw_urls=raw_urls,
            proxy=proxy,
            scan_sqli=scan_sqli,
            scan_xss=scan_xss,
            scan_lfi=scan_lfi,
        )

    # Run selected scans
    findings = []
    for url in valid_urls:
        if scan_sqli:
            findings.extend(test_sqli(url, proxy=proxy))
        if scan_xss:
            findings.extend(test_xss(url, proxy=proxy))
        if scan_lfi:
            findings.extend(test_lfi(url, proxy=proxy))

    # Sort findings by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda f: severity_order.get(f.get("severity", "low"), 4))

    return render_template(
        "scanner.html",
        findings=findings,
        urls_scanned=len(valid_urls),
        raw_urls="\n".join(valid_urls),
        proxy=proxy,
        scan_sqli=scan_sqli,
        scan_xss=scan_xss,
        scan_lfi=scan_lfi,
    )


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(debug=debug, host="127.0.0.1", port=5000)
