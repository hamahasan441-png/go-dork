"""Tests for dorker module — search engine scraping logic."""

from unittest.mock import patch, MagicMock

import pytest
from bs4 import BeautifulSoup

from dorker import (
    _extract_google,
    _extract_bing,
    _extract_yahoo,
    _extract_duck,
    _extract_shodan,
    _extract_ask,
    _is_valid_url,
    _make_request,
    search,
    ENGINES,
)


# ---------------------------------------------------------------------------
# _is_valid_url
# ---------------------------------------------------------------------------


class TestIsValidUrl:
    def test_http_url(self):
        assert _is_valid_url("http://example.com") is True

    def test_https_url(self):
        assert _is_valid_url("https://example.com/path?q=1") is True

    def test_no_scheme(self):
        assert _is_valid_url("example.com") is False

    def test_ftp_scheme(self):
        assert _is_valid_url("ftp://example.com") is False

    def test_empty_string(self):
        assert _is_valid_url("") is False

    def test_just_scheme(self):
        assert _is_valid_url("http://") is False

    def test_javascript_uri(self):
        assert _is_valid_url("javascript:alert(1)") is False

    def test_relative_path(self):
        assert _is_valid_url("/path/to/file") is False


# ---------------------------------------------------------------------------
# Extraction functions (unit-tested with crafted HTML)
# ---------------------------------------------------------------------------


class TestExtractGoogle:
    def test_extracts_urls(self):
        html = """
        <div>
            <a href="/url?q=https://example.com&sa=U&">Example</a>
            <a href="/url?q=https://other.com&sa=U&">Other</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_google(soup)
        assert urls == ["https://example.com", "https://other.com"]

    def test_ignores_non_result_links(self):
        html = '<a href="https://google.com/settings">Settings</a>'
        soup = BeautifulSoup(html, "html.parser")
        assert _extract_google(soup) == []

    def test_empty_page(self):
        soup = BeautifulSoup("", "html.parser")
        assert _extract_google(soup) == []


class TestExtractBing:
    def test_extracts_urls(self):
        html = """
        <ol>
            <li class="b_algo"><h2><a href="https://example.com">Example</a></h2></li>
            <li class="b_algo"><h2><a href="https://other.com">Other</a></h2></li>
        </ol>
        """
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_bing(soup)
        assert urls == ["https://example.com", "https://other.com"]

    def test_empty_results(self):
        html = '<div class="b_no">No results</div>'
        soup = BeautifulSoup(html, "html.parser")
        assert _extract_bing(soup) == []


class TestExtractYahoo:
    def test_extracts_urls_primary_selector(self):
        html = '<a class="ac-algo fz-l ac-21th lh-24" href="https://example.com">Result</a>'
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_yahoo(soup)
        assert urls == ["https://example.com"]

    def test_fallback_selector(self):
        html = '<h3 class="title"><a href="https://fallback.com">Fallback</a></h3>'
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_yahoo(soup)
        assert urls == ["https://fallback.com"]

    def test_empty_page(self):
        soup = BeautifulSoup("<p>Nothing</p>", "html.parser")
        assert _extract_yahoo(soup) == []


class TestExtractDuck:
    def test_extracts_primary_selector(self):
        html = '<a class="result__a" href="https://example.com">Example</a>'
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_duck(soup)
        assert urls == ["https://example.com"]

    def test_fallback_uddg(self):
        html = '<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Ffallback.com">Link</a>'
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_duck(soup)
        assert urls == ["https://fallback.com"]

    def test_empty_results(self):
        soup = BeautifulSoup("<html></html>", "html.parser")
        assert _extract_duck(soup) == []


class TestExtractShodan:
    def test_extracts_host_urls(self):
        html = '<a href="/host/1.2.3.4">1.2.3.4</a>'
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_shodan(soup)
        assert urls == ["https://www.shodan.io/host/1.2.3.4"]

    def test_ignores_non_host_links(self):
        html = '<a href="/search?query=test">Search</a>'
        soup = BeautifulSoup(html, "html.parser")
        assert _extract_shodan(soup) == []


class TestExtractAsk:
    def test_extracts_primary_selector(self):
        html = '<a class="PartialSearchResults-item-title-link" href="https://example.com">Title</a>'
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_ask(soup)
        assert urls == ["https://example.com"]

    def test_fallback_target_blank(self):
        html = '<a href="https://fallback.com" target="_blank">Link</a>'
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_ask(soup)
        assert urls == ["https://fallback.com"]

    def test_ignores_non_http(self):
        html = '<a href="javascript:void(0)" target="_blank">Bad</a>'
        soup = BeautifulSoup(html, "html.parser")
        assert _extract_ask(soup) == []


# ---------------------------------------------------------------------------
# _make_request (mocked HTTP)
# ---------------------------------------------------------------------------


class TestMakeRequest:
    @patch("dorker.requests.get")
    def test_get_request(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<html>ok</html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _make_request("http://example.com", {"q": "test"})
        assert result == "<html>ok</html>"
        mock_get.assert_called_once()

    @patch("dorker.requests.post")
    def test_post_request(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.text = "<html>posted</html>"
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = _make_request("http://example.com", {"q": "test"}, method="POST")
        assert result == "<html>posted</html>"
        mock_post.assert_called_once()

    @patch("dorker.requests.get")
    def test_request_with_proxy(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "ok"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _make_request("http://example.com", {}, proxy="socks5://127.0.0.1:9050")
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["proxies"] is not None

    @patch("dorker.requests.get")
    def test_request_failure_returns_empty(self, mock_get):
        import requests
        mock_get.side_effect = requests.RequestException("fail")
        result = _make_request("http://example.com", {})
        assert result == ""

    @patch("dorker.requests.get")
    def test_custom_headers_passed(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "ok"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _make_request("http://example.com", {}, headers={"X-Custom": "test"})
        call_kwargs = mock_get.call_args.kwargs
        assert "X-Custom" in call_kwargs["headers"]
        assert call_kwargs["headers"]["X-Custom"] == "test"


# ---------------------------------------------------------------------------
# search() — integration with mocked HTTP
# ---------------------------------------------------------------------------


class TestSearch:
    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            search("test", engine="nonexistent")

    @patch("dorker._make_request")
    def test_google_search_returns_urls(self, mock_req):
        html = """
        <div>
            <a href="/url?q=https://result1.com&sa=U&">R1</a>
            <a href="/url?q=https://result2.com&sa=U&">R2</a>
        </div>
        """
        mock_req.return_value = html

        results = search("test query", engine="google", pages=1)
        assert results == ["https://result1.com", "https://result2.com"]

    @patch("dorker._make_request")
    def test_search_deduplicates(self, mock_req):
        html = """
        <div>
            <a href="/url?q=https://dup.com&sa=U&">R1</a>
            <a href="/url?q=https://dup.com&sa=U&">R2</a>
        </div>
        """
        mock_req.return_value = html

        results = search("test", engine="google", pages=1)
        assert results == ["https://dup.com"]

    @patch("dorker._make_request")
    def test_search_empty_html_stops(self, mock_req):
        mock_req.return_value = ""
        results = search("test", engine="google", pages=3)
        assert results == []
        assert mock_req.call_count == 1

    @patch("dorker._make_request")
    def test_search_no_matches_stops(self, mock_req):
        mock_req.return_value = "<html><body>No results</body></html>"
        results = search("test", engine="google", pages=3)
        assert results == []
        # Stop after first page with no matches
        assert mock_req.call_count == 1

    @patch("dorker._make_request")
    def test_duck_single_page_only(self, mock_req):
        """DuckDuckGo doesn't support pagination, so max 1 page."""
        html = '<a class="result__a" href="https://duck-result.com">R</a>'
        mock_req.return_value = html

        results = search("test", engine="duck", pages=5)
        assert results == ["https://duck-result.com"]
        assert mock_req.call_count == 1

    @patch("dorker._make_request")
    def test_search_filters_invalid_urls(self, mock_req):
        html = """
        <div>
            <a href="/url?q=https://valid.com&sa=U&">Good</a>
            <a href="/url?q=not-a-url&sa=U&">Bad</a>
        </div>
        """
        mock_req.return_value = html

        results = search("test", engine="google", pages=1)
        assert results == ["https://valid.com"]


class TestEnginesConfig:
    """Verify ENGINES dictionary integrity."""

    @pytest.mark.parametrize("engine_name", ENGINES.keys())
    def test_engine_has_required_keys(self, engine_name):
        cfg = ENGINES[engine_name]
        for key in ("base_url", "extract", "build_params", "supports_pagination", "method"):
            assert key in cfg, f"Engine '{engine_name}' missing key '{key}'"

    @pytest.mark.parametrize("engine_name", ENGINES.keys())
    def test_engine_build_params_callable(self, engine_name):
        params = ENGINES[engine_name]["build_params"]("test", 0)
        assert isinstance(params, dict)

    @pytest.mark.parametrize("engine_name", ENGINES.keys())
    def test_engine_extract_callable(self, engine_name):
        soup = BeautifulSoup("", "html.parser")
        result = ENGINES[engine_name]["extract"](soup)
        assert isinstance(result, list)
