"""Tests for crawler module — URL crawler and link discovery."""

from unittest.mock import patch, MagicMock

import pytest
from bs4 import BeautifulSoup

from crawler import (
    _same_domain,
    _has_params,
    _extract_form_urls,
    crawl,
    MAX_CRAWL_URLS,
)


# ---------------------------------------------------------------------------
# _same_domain
# ---------------------------------------------------------------------------


class TestSameDomain:
    def test_exact_match(self):
        assert _same_domain("http://example.com/path", "example.com") is True

    def test_subdomain_match(self):
        assert _same_domain("http://sub.example.com/page", "example.com") is True

    def test_different_domain(self):
        assert _same_domain("http://other.com/page", "example.com") is False

    def test_with_port(self):
        assert _same_domain("http://example.com:8080/path", "example.com") is True

    def test_partial_match_not_subdomain(self):
        """notexample.com should not match example.com."""
        assert _same_domain("http://notexample.com", "example.com") is False

    def test_empty_url(self):
        assert _same_domain("", "example.com") is False

    def test_case_insensitive(self):
        assert _same_domain("http://Example.COM/path", "example.com") is True


# ---------------------------------------------------------------------------
# _has_params
# ---------------------------------------------------------------------------


class TestHasParams:
    def test_url_with_params(self):
        assert _has_params("http://example.com/page?id=1&name=test") is True

    def test_url_without_params(self):
        assert _has_params("http://example.com/page") is False

    def test_url_with_empty_query(self):
        assert _has_params("http://example.com/page?") is False

    def test_url_with_fragment_only(self):
        assert _has_params("http://example.com/page#section") is False

    def test_url_with_param_and_fragment(self):
        assert _has_params("http://example.com/page?id=1#sec") is True


# ---------------------------------------------------------------------------
# _extract_form_urls
# ---------------------------------------------------------------------------


class TestExtractFormUrls:
    def test_extracts_form_actions(self):
        html = """
        <form action="/login" method="post">
            <input type="text" name="user">
        </form>
        <form action="/search" method="get">
            <input type="text" name="q">
        </form>
        """
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_form_urls(soup, "http://example.com")
        assert urls == ["http://example.com/login", "http://example.com/search"]

    def test_absolute_action(self):
        html = '<form action="https://other.com/submit"></form>'
        soup = BeautifulSoup(html, "html.parser")
        urls = _extract_form_urls(soup, "http://example.com")
        assert urls == ["https://other.com/submit"]

    def test_no_forms(self):
        soup = BeautifulSoup("<p>No forms</p>", "html.parser")
        assert _extract_form_urls(soup, "http://example.com") == []

    def test_form_without_action(self):
        html = '<form><input type="text"></form>'
        soup = BeautifulSoup(html, "html.parser")
        assert _extract_form_urls(soup, "http://example.com") == []


# ---------------------------------------------------------------------------
# crawl() — with mocked _fetch
# ---------------------------------------------------------------------------


class TestCrawl:
    @patch("crawler._fetch")
    def test_basic_crawl(self, mock_fetch):
        """Crawl a single page with links."""
        mock_fetch.return_value = """
        <html>
            <a href="/page1">Page 1</a>
            <a href="/page2?id=5">Page 2</a>
            <a href="https://external.com">External</a>
        </html>
        """
        result = crawl("http://example.com", depth=1)
        assert "http://example.com/page1" in result["all_urls"]
        assert "http://example.com/page2?id=5" in result["param_urls"]
        assert "https://external.com" in result["external_urls"]

    @patch("crawler._fetch")
    def test_depth_1_no_following(self, mock_fetch):
        """depth=1 means only crawl the target page, don't follow links."""
        mock_fetch.return_value = '<a href="/page1">Link</a>'
        result = crawl("http://example.com", depth=1)
        # Should find the link but not crawl it
        assert "http://example.com/page1" in result["all_urls"]
        # _fetch called only once (for the target page)
        assert mock_fetch.call_count == 1

    @patch("crawler._fetch")
    def test_depth_2_follows_links(self, mock_fetch):
        """depth=2 means crawl the target page and follow links one level."""
        page1_html = '<a href="/page2">Page 2</a>'
        page2_html = '<a href="/page3">Page 3</a>'

        def fetch_side_effect(url, proxy=""):
            if "page2" in url:
                return page2_html
            return page1_html

        mock_fetch.side_effect = fetch_side_effect
        result = crawl("http://example.com", depth=2)
        assert "http://example.com/page2" in result["all_urls"]

    @patch("crawler._fetch")
    def test_skips_non_http_links(self, mock_fetch):
        mock_fetch.return_value = """
        <a href="javascript:void(0)">JS</a>
        <a href="mailto:test@example.com">Email</a>
        <a href="tel:123">Phone</a>
        <a href="#section">Hash</a>
        <a href="http://example.com/real">Real</a>
        """
        result = crawl("http://example.com", depth=1)
        assert "http://example.com/real" in result["all_urls"]
        assert len(result["all_urls"]) == 1

    @patch("crawler._fetch")
    def test_extracts_form_urls(self, mock_fetch):
        mock_fetch.return_value = '<form action="/submit"></form>'
        result = crawl("http://example.com", depth=1)
        assert "http://example.com/submit" in result["form_urls"]

    @patch("crawler._fetch")
    def test_extracts_script_src(self, mock_fetch):
        mock_fetch.return_value = '<script src="/js/app.js"></script>'
        result = crawl("http://example.com", depth=1)
        assert "http://example.com/js/app.js" in result["all_urls"]

    @patch("crawler._fetch")
    def test_empty_response_skips(self, mock_fetch):
        mock_fetch.return_value = ""
        result = crawl("http://example.com", depth=2)
        assert result["all_urls"] == []

    @patch("crawler._fetch")
    def test_deduplicates_urls(self, mock_fetch):
        mock_fetch.return_value = """
        <a href="/page1">Link 1</a>
        <a href="/page1">Link 1 again</a>
        """
        result = crawl("http://example.com", depth=1)
        page1_count = result["all_urls"].count("http://example.com/page1")
        assert page1_count == 1

    @patch("crawler._fetch")
    def test_removes_fragments(self, mock_fetch):
        mock_fetch.return_value = """
        <a href="/page1#top">Link</a>
        <a href="/page1#bottom">Same page</a>
        """
        result = crawl("http://example.com", depth=1)
        # Both should resolve to the same URL without fragment
        found = [u for u in result["all_urls"] if "page1" in u]
        assert len(found) == 1

    @patch("crawler._fetch")
    def test_max_crawl_limit(self, mock_fetch):
        """Crawl should stop after MAX_CRAWL_URLS pages visited."""
        # Generate HTML with many links
        links = "".join(f'<a href="/page{i}">P{i}</a>' for i in range(300))
        mock_fetch.return_value = f"<html>{links}</html>"

        result = crawl("http://example.com", depth=3)
        # The total number of visited pages should be capped
        assert mock_fetch.call_count <= MAX_CRAWL_URLS + 1

    @patch("crawler._fetch")
    def test_return_structure(self, mock_fetch):
        mock_fetch.return_value = "<html></html>"
        result = crawl("http://example.com", depth=1)
        assert "all_urls" in result
        assert "param_urls" in result
        assert "form_urls" in result
        assert "external_urls" in result
        assert isinstance(result["all_urls"], list)
        assert isinstance(result["param_urls"], list)
        assert isinstance(result["form_urls"], list)
        assert isinstance(result["external_urls"], list)


# ---------------------------------------------------------------------------
# _fetch — SSRF protection and proxy handling
# ---------------------------------------------------------------------------


class TestFetch:
    @patch("crawler.is_safe_url")
    def test_blocks_unsafe_url(self, mock_safe):
        """_fetch should return empty string for unsafe URLs."""
        from crawler import _fetch
        mock_safe.return_value = False
        result = _fetch("http://127.0.0.1/admin")
        assert result == ""

    @patch("crawler.requests.get")
    @patch("crawler.is_safe_url")
    def test_passes_proxy(self, mock_safe, mock_get):
        from crawler import _fetch
        mock_safe.return_value = True
        mock_resp = MagicMock()
        mock_resp.text = "ok"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _fetch("http://example.com", proxy="http://proxy:8080")
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["proxies"] is not None
        assert call_kwargs["headers"]["Connection"] == "close"

    @patch("crawler.requests.get")
    @patch("crawler.is_safe_url")
    def test_request_failure_returns_empty(self, mock_safe, mock_get):
        import requests as req_lib
        from crawler import _fetch
        mock_safe.return_value = True
        mock_get.side_effect = req_lib.RequestException("timeout")
        result = _fetch("http://example.com")
        assert result == ""

    @patch("crawler.requests.get")
    @patch("crawler.is_safe_url")
    def test_successful_fetch(self, mock_safe, mock_get):
        from crawler import _fetch
        mock_safe.return_value = True
        mock_resp = MagicMock()
        mock_resp.text = "<html>content</html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch("http://example.com")
        assert result == "<html>content</html>"


# ---------------------------------------------------------------------------
# Additional crawler edge cases
# ---------------------------------------------------------------------------


class TestCrawlEdgeCases:
    @patch("crawler._fetch")
    def test_crawl_with_proxy(self, mock_fetch):
        mock_fetch.return_value = '<a href="/page">Link</a>'
        result = crawl("http://example.com", depth=1, proxy="http://proxy:8080")
        assert isinstance(result, dict)
        # Verify proxy was passed through
        mock_fetch.assert_called_with("http://example.com", proxy="http://proxy:8080")

    @patch("crawler._fetch")
    def test_subdomain_links_included(self, mock_fetch):
        mock_fetch.return_value = '<a href="http://sub.example.com/page">Sub</a>'
        result = crawl("http://example.com", depth=1)
        assert "http://sub.example.com/page" in result["all_urls"]

    @patch("crawler._fetch")
    def test_same_url_not_crawled_twice(self, mock_fetch):
        """When the same URL appears multiple times, it should only be fetched once."""
        mock_fetch.return_value = """
        <a href="/page">Link</a>
        <a href="/page">Link again</a>
        """
        result = crawl("http://example.com", depth=2)
        # /page should appear once in all_urls
        count = result["all_urls"].count("http://example.com/page")
        assert count <= 1
