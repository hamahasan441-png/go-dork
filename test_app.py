"""Tests for app module — Flask web application routes."""

from unittest.mock import patch

import pytest

from app import app


@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    # Disable rate limiter in tests
    from app import limiter
    limiter.enabled = False
    with app.test_client() as c:
        yield c
    limiter.enabled = True


# ---------------------------------------------------------------------------
# Index / Search
# ---------------------------------------------------------------------------


class TestIndex:
    def test_get_index(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_index_contains_engines(self, client):
        resp = client.get("/")
        assert b"google" in resp.data.lower()


class TestSearch:
    def test_search_missing_query(self, client):
        resp = client.post("/search", data={"query": "", "engine": "google"})
        assert resp.status_code == 200
        assert b"Query is required" in resp.data

    def test_search_invalid_engine(self, client):
        resp = client.post("/search", data={"query": "test", "engine": "invalid_eng"})
        assert resp.status_code == 200
        assert b"Unknown engine" in resp.data

    @patch("app.search")
    def test_search_success(self, mock_search, client):
        mock_search.return_value = ["https://result1.com", "https://result2.com"]
        resp = client.post("/search", data={
            "query": "test query",
            "engine": "google",
            "pages": "1",
        })
        assert resp.status_code == 200
        mock_search.assert_called_once()

    @patch("app.search")
    def test_search_with_proxy(self, mock_search, client):
        mock_search.return_value = []
        resp = client.post("/search", data={
            "query": "test",
            "engine": "google",
            "proxy": "http://proxy:8080",
        })
        assert resp.status_code == 200

    def test_search_invalid_pages_defaults(self, client):
        with patch("app.search") as mock_search:
            mock_search.return_value = []
            resp = client.post("/search", data={
                "query": "test",
                "engine": "google",
                "pages": "abc",
            })
            assert resp.status_code == 200

    def test_search_negative_pages_clamped(self, client):
        with patch("app.search") as mock_search:
            mock_search.return_value = []
            resp = client.post("/search", data={
                "query": "test",
                "engine": "google",
                "pages": "-5",
            })
            assert resp.status_code == 200

    # --- Header validation ---

    @patch("app.search")
    def test_search_valid_headers(self, mock_search, client):
        mock_search.return_value = []
        resp = client.post("/search", data={
            "query": "test",
            "engine": "google",
            "headers": "X-Custom: value\nAccept: text/html",
        })
        assert resp.status_code == 200
        # Verify custom headers were passed
        call_kwargs = mock_search.call_args
        assert call_kwargs.kwargs["headers"]["X-Custom"] == "value"

    def test_search_invalid_header_name(self, client):
        resp = client.post("/search", data={
            "query": "test",
            "engine": "google",
            "headers": "Invalid Header Name: value",
        })
        assert resp.status_code == 200
        assert b"Invalid header name" in resp.data

    def test_search_control_chars_in_header_value(self, client):
        resp = client.post("/search", data={
            "query": "test",
            "engine": "google",
            "headers": "X-Bad: value\x00evil",
        })
        assert resp.status_code == 200
        assert b"Invalid characters" in resp.data


# ---------------------------------------------------------------------------
# Dork Maker
# ---------------------------------------------------------------------------


class TestDorkMaker:
    def test_get_dorkmaker(self, client):
        resp = client.get("/dorkmaker")
        assert resp.status_code == 200

    def test_build_query(self, client):
        resp = client.post("/dorkmaker/build", data={
            "operator": ["site", "inurl"],
            "value": ["example.com", "admin"],
        })
        assert resp.status_code == 200

    def test_build_query_with_negation(self, client):
        resp = client.post("/dorkmaker/build", data={
            "operator": ["site"],
            "value": ["example.com"],
            "negate_0": "1",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------


class TestCrawler:
    def test_get_crawler(self, client):
        resp = client.get("/crawler")
        assert resp.status_code == 200

    def test_crawl_missing_url(self, client):
        resp = client.post("/crawler/crawl", data={"target_url": ""})
        assert resp.status_code == 200
        assert b"Target URL is required" in resp.data

    def test_crawl_invalid_url(self, client):
        resp = client.post("/crawler/crawl", data={"target_url": "not-a-url"})
        assert resp.status_code == 200
        assert b"Invalid URL" in resp.data

    @patch("app.is_safe_url")
    def test_crawl_blocks_private_url(self, mock_safe, client):
        mock_safe.return_value = False
        resp = client.post("/crawler/crawl", data={
            "target_url": "http://192.168.1.1",
        })
        assert resp.status_code == 200
        assert b"private" in resp.data.lower() or b"internal" in resp.data.lower()

    @patch("app.crawl")
    @patch("app.is_safe_url")
    def test_crawl_success(self, mock_safe, mock_crawl, client):
        mock_safe.return_value = True
        mock_crawl.return_value = {
            "all_urls": ["http://example.com/page1"],
            "param_urls": [],
            "form_urls": [],
            "external_urls": [],
        }
        resp = client.post("/crawler/crawl", data={
            "target_url": "http://example.com",
            "depth": "2",
        })
        assert resp.status_code == 200

    def test_crawl_depth_clamped_high(self, client):
        with patch("app.crawl") as mock_crawl, patch("app.is_safe_url", return_value=True):
            mock_crawl.return_value = {
                "all_urls": [], "param_urls": [], "form_urls": [], "external_urls": []
            }
            resp = client.post("/crawler/crawl", data={
                "target_url": "http://example.com",
                "depth": "100",
            })
            assert resp.status_code == 200
            # Depth should be clamped to 5
            mock_crawl.assert_called_once()
            assert mock_crawl.call_args.kwargs["depth"] == 5

    def test_crawl_invalid_depth_defaults(self, client):
        with patch("app.crawl") as mock_crawl, patch("app.is_safe_url", return_value=True):
            mock_crawl.return_value = {
                "all_urls": [], "param_urls": [], "form_urls": [], "external_urls": []
            }
            resp = client.post("/crawler/crawl", data={
                "target_url": "http://example.com",
                "depth": "abc",
            })
            assert resp.status_code == 200
            assert mock_crawl.call_args.kwargs["depth"] == 2


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class TestScanner:
    def test_get_scanner(self, client):
        resp = client.get("/scanner")
        assert resp.status_code == 200

    def test_scan_no_urls(self, client):
        resp = client.post("/scanner/scan", data={"urls": ""})
        assert resp.status_code == 200
        assert b"valid URL" in resp.data

    def test_scan_invalid_url(self, client):
        resp = client.post("/scanner/scan", data={"urls": "not-a-url"})
        assert resp.status_code == 200

    @patch("app.test_sqli")
    @patch("app.test_xss")
    @patch("app.test_lfi")
    @patch("app.is_safe_url")
    def test_scan_success(self, mock_safe, mock_lfi, mock_xss, mock_sqli, client):
        mock_safe.return_value = True
        mock_sqli.return_value = []
        mock_xss.return_value = []
        mock_lfi.return_value = []
        resp = client.post("/scanner/scan", data={
            "urls": "http://example.com/page?id=1",
            "scan_sqli": "1",
            "scan_xss": "1",
            "scan_lfi": "1",
        })
        assert resp.status_code == 200

    @patch("app.test_sqli")
    @patch("app.test_xss")
    @patch("app.test_lfi")
    @patch("app.is_safe_url")
    def test_scan_with_findings(self, mock_safe, mock_lfi, mock_xss, mock_sqli, client):
        mock_safe.return_value = True
        mock_sqli.return_value = [{
            "type": "SQLi", "url": "http://example.com/page?id=1",
            "param": "id", "payload": "'", "evidence": "syntax error",
            "severity": "high",
        }]
        mock_xss.return_value = []
        mock_lfi.return_value = []
        resp = client.post("/scanner/scan", data={
            "urls": "http://example.com/page?id=1",
            "scan_sqli": "1",
        })
        assert resp.status_code == 200

    @patch("app.is_safe_url")
    def test_scan_blocks_private_url(self, mock_safe, client):
        mock_safe.return_value = False
        resp = client.post("/scanner/scan", data={
            "urls": "http://192.168.1.1/page?id=1",
        })
        assert resp.status_code == 200
        assert b"private" in resp.data.lower() or b"internal" in resp.data.lower()

    @patch("app.test_sqli")
    @patch("app.test_xss")
    @patch("app.test_lfi")
    @patch("app.is_safe_url")
    def test_scan_multiline_urls(self, mock_safe, mock_lfi, mock_xss, mock_sqli, client):
        """URLs submitted as a newline-separated textarea."""
        mock_safe.return_value = True
        mock_sqli.return_value = []
        mock_xss.return_value = []
        mock_lfi.return_value = []
        resp = client.post("/scanner/scan", data={
            "urls": "http://a.com/p?id=1\nhttp://b.com/q?x=2",
            "scan_sqli": "1",
        })
        assert resp.status_code == 200

    @patch("app.test_sqli")
    @patch("app.test_xss")
    @patch("app.test_lfi")
    @patch("app.is_safe_url")
    def test_scan_defaults_all_types_when_none_checked(self, mock_safe, mock_lfi, mock_xss, mock_sqli, client):
        """If no scan type checkboxes are submitted, all types default to True."""
        mock_safe.return_value = True
        mock_sqli.return_value = []
        mock_xss.return_value = []
        mock_lfi.return_value = []
        resp = client.post("/scanner/scan", data={
            "urls": "http://example.com/page?id=1",
        })
        assert resp.status_code == 200
        # All three scan functions should have been called
        mock_sqli.assert_called()
        mock_xss.assert_called()
        mock_lfi.assert_called()

    @patch("app.test_sqli")
    @patch("app.test_xss")
    @patch("app.test_lfi")
    @patch("app.is_safe_url")
    def test_scan_findings_sorted_by_severity(self, mock_safe, mock_lfi, mock_xss, mock_sqli, client):
        mock_safe.return_value = True
        mock_sqli.return_value = [{"type": "SQLi", "severity": "high", "url": "u", "param": "p", "payload": "x", "evidence": "e"}]
        mock_xss.return_value = [{"type": "XSS", "severity": "medium", "url": "u", "param": "p", "payload": "x", "evidence": "e"}]
        mock_lfi.return_value = [{"type": "LFI", "severity": "critical", "url": "u", "param": "p", "payload": "x", "evidence": "e"}]
        resp = client.post("/scanner/scan", data={
            "urls": "http://example.com/page?id=1",
            "scan_sqli": "1",
            "scan_xss": "1",
            "scan_lfi": "1",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Additional edge case tests for search route
# ---------------------------------------------------------------------------


class TestSearchEdgeCases:
    def test_search_whitespace_only_query(self, client):
        resp = client.post("/search", data={"query": "   ", "engine": "google"})
        assert resp.status_code == 200
        assert b"Query is required" in resp.data

    @patch("app.search")
    def test_search_headers_without_colon_ignored(self, mock_search, client):
        """Header lines without a colon separator should be silently skipped."""
        mock_search.return_value = []
        resp = client.post("/search", data={
            "query": "test",
            "engine": "google",
            "headers": "no-colon-here",
        })
        assert resp.status_code == 200

    @patch("app.search")
    def test_search_empty_header_lines_skipped(self, mock_search, client):
        mock_search.return_value = []
        resp = client.post("/search", data={
            "query": "test",
            "engine": "google",
            "headers": "\n\n\n",
        })
        assert resp.status_code == 200

    @patch("app.search")
    def test_search_pages_very_large(self, mock_search, client):
        mock_search.return_value = []
        resp = client.post("/search", data={
            "query": "test",
            "engine": "google",
            "pages": "999",
        })
        assert resp.status_code == 200

    @patch("app.search")
    def test_search_result_count_in_response(self, mock_search, client):
        mock_search.return_value = ["https://r1.com", "https://r2.com"]
        resp = client.post("/search", data={
            "query": "test",
            "engine": "google",
        })
        assert resp.status_code == 200

    @patch("app.search")
    def test_search_all_engines(self, mock_search, client):
        """All engine names should be accepted."""
        from dorker import ENGINES
        mock_search.return_value = []
        for engine_name in ENGINES:
            resp = client.post("/search", data={
                "query": "test",
                "engine": engine_name,
            })
            assert resp.status_code == 200, f"Engine '{engine_name}' failed"


# ---------------------------------------------------------------------------
# Additional edge case tests for crawler route
# ---------------------------------------------------------------------------


class TestCrawlerEdgeCases:
    def test_crawl_ftp_url_rejected(self, client):
        resp = client.post("/crawler/crawl", data={"target_url": "ftp://example.com"})
        assert resp.status_code == 200
        assert b"Invalid URL" in resp.data

    def test_crawl_negative_depth_clamped(self, client):
        with patch("app.crawl") as mock_crawl, patch("app.is_safe_url", return_value=True):
            mock_crawl.return_value = {
                "all_urls": [], "param_urls": [], "form_urls": [], "external_urls": []
            }
            resp = client.post("/crawler/crawl", data={
                "target_url": "http://example.com",
                "depth": "-1",
            })
            assert resp.status_code == 200
            assert mock_crawl.call_args.kwargs["depth"] == 1


# ---------------------------------------------------------------------------
# Additional edge case tests for scanner route
# ---------------------------------------------------------------------------


class TestScannerEdgeCases:
    @patch("app.test_sqli")
    @patch("app.test_xss")
    @patch("app.test_lfi")
    @patch("app.is_safe_url")
    def test_scan_only_sqli_selected(self, mock_safe, mock_lfi, mock_xss, mock_sqli, client):
        mock_safe.return_value = True
        mock_sqli.return_value = []
        mock_xss.return_value = []
        mock_lfi.return_value = []
        resp = client.post("/scanner/scan", data={
            "urls": "http://example.com/page?id=1",
            "scan_sqli": "1",
        })
        assert resp.status_code == 200
        mock_sqli.assert_called()
        mock_xss.assert_not_called()
        mock_lfi.assert_not_called()

    @patch("app.test_sqli")
    @patch("app.test_xss")
    @patch("app.test_lfi")
    @patch("app.is_safe_url")
    def test_scan_only_xss_selected(self, mock_safe, mock_lfi, mock_xss, mock_sqli, client):
        mock_safe.return_value = True
        mock_sqli.return_value = []
        mock_xss.return_value = []
        mock_lfi.return_value = []
        resp = client.post("/scanner/scan", data={
            "urls": "http://example.com/page?id=1",
            "scan_xss": "1",
        })
        assert resp.status_code == 200
        mock_sqli.assert_not_called()
        mock_xss.assert_called()
        mock_lfi.assert_not_called()

    def test_scan_mixed_valid_invalid_urls(self, client):
        with patch("app.test_sqli", return_value=[]), \
             patch("app.test_xss", return_value=[]), \
             patch("app.test_lfi", return_value=[]), \
             patch("app.is_safe_url", return_value=True):
            resp = client.post("/scanner/scan", data={
                "urls": "http://example.com/p?id=1\nnot-a-url\nhttp://other.com/q?x=2",
            })
            assert resp.status_code == 200
