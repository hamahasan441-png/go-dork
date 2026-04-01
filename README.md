# go-dork

[![License](https://img.shields.io/badge/license-MIT-_red.svg)](https://opensource.org/licenses/MIT)
[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/dwisiswant0/go-dork/issues)

The fastest dork scanner — now with a **Python + Flask web frontend** featuring an advanced dork maker, URL crawler, and vulnerability scanner.

<img src="https://user-images.githubusercontent.com/25837540/111008561-f22f9c80-83c3-11eb-8500-fb63456a4614.png" height="350">

There are also various search engines supported by go-dork, including Google, Shodan, Bing, Duck, Yahoo, Ask, Startpage, and Brave.

- [Install](#install)
- [Usage](#usage)
  - [Web Interface](#web-interface)
  - [Search Engines](#search-engines)
  - [Dork Maker](#dork-maker)
  - [URL Crawler](#url-crawler)
  - [Vulnerability Scanner](#vulnerability-scanner)
  - [Advanced Options](#advanced-options)
  - [Result Export](#result-export)
- [Configuration](#configuration)
- [Docker](#docker)
- [Go CLI (Legacy)](#go-cli-legacy)
- [Supporting Materials](#supporting-materials)
- [Help & Bugs](#help--bugs)
- [TODOs](#todos)
- [License](#license)
- [Version](#version)

## Install

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
```

## Usage

### Web Interface

Start the Flask development server:

```bash
python app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

The web interface provides four main tools accessible via the top navigation bar:

### Search Engines

The **Search** page lets you run dork queries across multiple search engines:

| Engine        | Description                        |
|---------------|------------------------------------|
| **Google**    | Google Search (default)            |
| **Shodan**    | Shodan IoT search engine           |
| **Bing**      | Microsoft Bing                     |
| **Duck**      | DuckDuckGo (single page only)      |
| **Yahoo**     | Yahoo Search                       |
| **Ask**       | Ask.com                            |
| **Startpage** | Startpage (privacy-focused)        |
| **Brave**     | Brave Search                       |

### Dork Maker

The **Dork Maker** page helps you build advanced dork queries:

- **Query Builder**: Add multiple operators (site, inurl, intitle, intext, filetype, ext, etc.) with values and optional NOT negation
- **Preset Templates**: Browse categories of pre-built dorks — Admin Panels, Login Pages, Exposed Files, Database Exposure, Sensitive Information, Vulnerable Servers, Error Messages, and IoT/Cameras
- **Operator Reference**: Quick reference table for all supported dork operators
- Generated queries can be sent directly to the Search page with one click

### URL Crawler

The **Crawler** page discovers URLs on a target website:

- Crawls target pages up to a configurable depth (1–5 levels)
- Collects all internal URLs, URLs with query parameters, form action URLs, and external URLs
- Categorizes results with expandable sections
- URLs with parameters can be sent directly to the Vulnerability Scanner
- **robots.txt support**: Optionally respect the target's robots.txt directives
- **Sitemap parsing**: Optionally parse sitemap.xml for additional URL discovery

### Vulnerability Scanner

The **Scanner** page tests URLs for common web vulnerabilities:

| Scan Type         | Description | Severity |
|-------------------|-------------|----------|
| **SQLi**          | SQL Injection — tests for error-based SQL injection using common payloads | High |
| **XSS**           | Cross-Site Scripting — tests for reflected XSS using marker-based payloads | High–Medium |
| **LFI**           | Local File Inclusion — tests for path traversal and file inclusion | Critical |
| **Open Redirect** | Open Redirect — tests redirect-related parameters for unvalidated redirects | Medium |

- Accepts multiple URLs (one per line)
- Configurable scan types (SQLi, XSS, LFI, Open Redirect)
- Results sorted by severity with detailed findings table
- Concurrent scanning for faster results
- Optional proxy support for all scans

> **⚠️ Disclaimer:** Only scan URLs you have explicit permission to test. Unauthorized scanning may violate laws and regulations.

### Advanced Options

- **Proxy:** Enter an HTTP or SOCKS5 proxy URL (e.g. `http://127.0.0.1:8080` or `socks5://127.0.0.1:1080`)
- **Custom Headers:** Add custom HTTP headers, one per line in `Name: Value` format (e.g. `Cookie: session=abc123`)

### Result Export

All results can be exported in multiple formats:

- **JSON** — Structured data format
- **CSV** — Spreadsheet-compatible format
- **TXT** — Plain text (one URL per line)

Export buttons appear automatically after search, crawl, or scan results.

## Configuration

go-dork can be configured via environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_DEBUG` | `0` | Enable Flask debug mode |
| `FLASK_SECRET_KEY` | *random* | Secret key for CSRF protection |
| `GODORK_REQUEST_TIMEOUT` | `15` | HTTP request timeout in seconds |
| `GODORK_MAX_RETRIES` | `3` | Maximum retry attempts for failed requests |
| `GODORK_MAX_CRAWL_URLS` | `200` | Maximum URLs to crawl per target |

See `.env.example` for a template.

## Docker

Run with Docker:

```bash
docker build -t go-dork .
docker run -p 5000:5000 go-dork
```

Or with Docker Compose:

```bash
docker compose up
```

## Security Features

- **CSRF Protection**: All forms are protected with CSRF tokens via Flask-WTF
- **Rate Limiting**: API endpoints have per-route rate limits to prevent abuse
- **Content Security Policy**: CSP headers prevent XSS in the web UI
- **SSRF Prevention**: All URLs are validated against private/internal networks
- **HTTP Header Validation**: Custom headers are validated per RFC 7230

## Go CLI (Legacy)

The original Go CLI is still available with enhanced features:

```bash
> GO111MODULE=on go install github.com/dwisiswant0/go-dork@latest
> go-dork -q "inurl:'/admin'" -e google -p 3 -t 30 -d 1000
```

| Flag | Description | Default |
|------|-------------|---------|
| `-q, --query` | Search query | *required* |
| `-e, --engine` | Search engine | `google` |
| `-p, --page` | Number of pages | `1` |
| `-H, --header` | Custom HTTP header | — |
| `-x, --proxy` | HTTP/SOCKS5 proxy | — |
| `-t, --timeout` | Request timeout (seconds) | `30` |
| `-d, --delay` | Delay between requests (ms) | `0` |
| `-s, --silent` | Silent mode | `false` |

## Supporting Materials

- Hazana. _[Dorking on Steroids](https://hazanasec.github.io/2021-03-11-Dorking-on-Steriods/)_, 11 Mar. 2021, https://hazanasec.github.io/2021-03-11-Dorking-on-Steriods/.

## Help & Bugs

If you are still confused or found a bug, please [open the issue](https://github.com/dwisiswant0/go-dork/issues). All bug reports are appreciated, some features have not been tested yet due to lack of free time.

## TODOs

- [x] Fixes Yahoo regexes
- [x] Fixes Google regexes if using custom User-Agent
- [x] Stopping if there's no results & page flag was set
- [x] DuckDuckGo next page
- [x] HTTP timeouts and retry logic
- [x] Rate limiting and delay support
- [x] CSRF protection
- [x] Result export (JSON, CSV, TXT)
- [x] Open Redirect detection
- [x] CI/CD pipeline
- [x] Docker support
- [x] robots.txt and sitemap.xml support

## License

MIT. See `LICENSE` for more details.
