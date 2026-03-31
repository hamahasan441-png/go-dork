"""Flask web application for go-dork search engine dorking tool."""

import logging
import os
import re

from flask import Flask, render_template, request

from dorker import ENGINES, search

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regex to validate HTTP header names (RFC 7230 token characters)
_VALID_HEADER_NAME = re.compile(r"^[A-Za-z0-9!#$%&'*+\-.^_`|~]+$")
# Reject control characters in header values
_INVALID_HEADER_VALUE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


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


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(debug=debug, host="127.0.0.1", port=5000)
