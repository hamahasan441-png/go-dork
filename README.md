# go-dork

[![License](https://img.shields.io/badge/license-MIT-_red.svg)](https://opensource.org/licenses/MIT)
[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/dwisiswant0/go-dork/issues)

The fastest dork scanner — now with a **Python + Flask web frontend** featuring an advanced dork maker, URL crawler, and vulnerability scanner.

<img src="https://user-images.githubusercontent.com/25837540/111008561-f22f9c80-83c3-11eb-8500-fb63456a4614.png" height="350">

There are also various search engines supported by go-dork, including Google, Shodan, Bing, Duck, Yahoo and Ask.

- [Install](#install)
- [Usage](#usage)
  - [Web Interface](#web-interface)
  - [Search Engines](#search-engines)
  - [Dork Maker](#dork-maker)
  - [URL Crawler](#url-crawler)
  - [Vulnerability Scanner](#vulnerability-scanner)
  - [Advanced Options](#advanced-options)
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

| Engine       | Description                        |
|--------------|------------------------------------|
| **Google**   | Google Search (default)            |
| **Shodan**   | Shodan IoT search engine           |
| **Bing**     | Microsoft Bing                     |
| **Duck**     | DuckDuckGo (single page only)      |
| **Yahoo**    | Yahoo Search                       |
| **Ask**      | Ask.com                            |

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

### Vulnerability Scanner

The **Scanner** page tests URLs for common web vulnerabilities:

| Scan Type | Description | Severity |
|-----------|-------------|----------|
| **SQLi**  | SQL Injection — tests for error-based SQL injection using common payloads | High |
| **XSS**   | Cross-Site Scripting — tests for reflected XSS using marker-based payloads | High–Medium |
| **LFI**   | Local File Inclusion — tests for path traversal and file inclusion | Critical |

- Accepts multiple URLs (one per line)
- Configurable scan types (SQLi, XSS, LFI)
- Results sorted by severity with detailed findings table
- Optional proxy support for all scans

> **⚠️ Disclaimer:** Only scan URLs you have explicit permission to test. Unauthorized scanning may violate laws and regulations.

### Advanced Options

- **Proxy:** Enter an HTTP or SOCKS5 proxy URL (e.g. `http://127.0.0.1:8080` or `socks5://127.0.0.1:1080`)
- **Custom Headers:** Add custom HTTP headers, one per line in `Name: Value` format (e.g. `Cookie: session=abc123`)

## Go CLI (Legacy)

The original Go CLI is still available. See the Go source files (`main.go`, etc.) for details, or [download a prebuilt binary](https://github.com/dwisiswant0/go-dork/releases).

```bash
> GO111MODULE=on go install github.com/dwisiswant0/go-dork@latest
> go-dork -q "inurl:'/admin'" -e google -p 3
```

## Supporting Materials

- Hazana. _[Dorking on Steroids](https://hazanasec.github.io/2021-03-11-Dorking-on-Steriods/)_, 11 Mar. 2021, https://hazanasec.github.io/2021-03-11-Dorking-on-Steriods/.

## Help & Bugs

If you are still confused or found a bug, please [open the issue](https://github.com/dwisiswant0/go-dork/issues). All bug reports are appreciated, some features have not been tested yet due to lack of free time.

## TODOs

- [ ] Fixes Yahoo regexes
- [ ] Fixes Google regexes if using custom User-Agent
- [x] Stopping if there's no results & page flag was set
- [ ] DuckDuckGo next page

## License

MIT. See `LICENSE` for more details.
