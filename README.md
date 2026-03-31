# go-dork

[![License](https://img.shields.io/badge/license-MIT-_red.svg)](https://opensource.org/licenses/MIT)
[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/dwisiswant0/go-dork/issues)

The fastest dork scanner — now with a **Python + Flask web frontend**.

<img src="https://user-images.githubusercontent.com/25837540/111008561-f22f9c80-83c3-11eb-8500-fb63456a4614.png" height="350">

There are also various search engines supported by go-dork, including Google, Shodan, Bing, Duck, Yahoo and Ask.

- [Install](#install)
- [Usage](#usage)
  - [Web Interface](#web-interface)
  - [Search Engines](#search-engines)
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

The web interface provides:
- A search form with a query input field
- A dropdown to select the search engine
- Page count selector for pagination
- Advanced options for proxy and custom HTTP headers
- Results displayed as clickable links

### Search Engines

The following search engines are supported:

| Engine       | Description                        |
|--------------|------------------------------------|
| **Google**   | Google Search (default)            |
| **Shodan**   | Shodan IoT search engine           |
| **Bing**     | Microsoft Bing                     |
| **Duck**     | DuckDuckGo (single page only)      |
| **Yahoo**    | Yahoo Search                       |
| **Ask**      | Ask.com                            |

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
