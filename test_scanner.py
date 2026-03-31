"""Tests for scanner module — vulnerability detection (SQLi, XSS, LFI)."""

from unittest.mock import patch

import pytest

import scanner as scanner_mod
from scanner import (
    _inject_param,
    _get_params,
    scan_url,
    scan_urls,
    SQLI_PAYLOADS,
    SQLI_ERROR_PATTERNS,
    XSS_MARKER,
    XSS_PAYLOADS,
    LFI_PAYLOADS,
    LFI_SUCCESS_PATTERNS,
)

# Alias to avoid pytest collecting these as tests (they start with "test_")
sqli_test = scanner_mod.test_sqli
xss_test = scanner_mod.test_xss
lfi_test = scanner_mod.test_lfi


# ---------------------------------------------------------------------------
# _get_params
# ---------------------------------------------------------------------------


class TestGetParams:
    def test_single_param(self):
        assert _get_params("http://example.com/page?id=1") == ["id"]

    def test_multiple_params(self):
        params = _get_params("http://example.com/page?id=1&name=test&page=2")
        assert sorted(params) == ["id", "name", "page"]

    def test_no_params(self):
        assert _get_params("http://example.com/page") == []

    def test_blank_value(self):
        assert _get_params("http://example.com/page?q=") == ["q"]


# ---------------------------------------------------------------------------
# _inject_param
# ---------------------------------------------------------------------------


class TestInjectParam:
    def test_replace_single_param(self):
        result = _inject_param("http://example.com/page?id=1", "id", "PAYLOAD")
        assert "id=PAYLOAD" in result

    def test_replace_specific_param_only(self):
        url = "http://example.com/page?id=1&name=test"
        result = _inject_param(url, "id", "INJECTED")
        assert "id=INJECTED" in result
        assert "name=test" in result

    def test_preserves_url_structure(self):
        result = _inject_param("http://example.com/page?id=1", "id", "new")
        assert result.startswith("http://example.com/page?")

    def test_special_characters_in_payload(self):
        result = _inject_param(
            "http://example.com/page?q=test", "q", "' OR '1'='1"
        )
        assert "q=" in result


# ---------------------------------------------------------------------------
# sqli_test (mocked _fetch)
# ---------------------------------------------------------------------------


class TestSqli:
    @patch("scanner._fetch")
    def test_detects_sql_error(self, mock_fetch):
        mock_fetch.return_value = (
            "Error: you have an error in your sql syntax near 'test'"
        )
        findings = sqli_test("http://example.com/page?id=1")
        assert len(findings) >= 1
        assert findings[0]["type"] == "SQLi"
        assert findings[0]["severity"] == "high"
        assert findings[0]["param"] == "id"

    @patch("scanner._fetch")
    def test_detects_mysql_warning(self, mock_fetch):
        mock_fetch.return_value = "Warning: mysql_fetch_array(): supplied argument"
        findings = sqli_test("http://example.com/page?id=1")
        assert len(findings) >= 1
        assert findings[0]["type"] == "SQLi"

    @patch("scanner._fetch")
    def test_detects_postgres_error(self, mock_fetch):
        mock_fetch.return_value = "pg_query(): Query failed: error"
        findings = sqli_test("http://example.com/page?id=1")
        assert len(findings) >= 1

    @patch("scanner._fetch")
    def test_detects_oracle_error(self, mock_fetch):
        mock_fetch.return_value = "ORA-01756: quoted string not properly terminated"
        findings = sqli_test("http://example.com/page?id=1")
        assert len(findings) >= 1

    @patch("scanner._fetch")
    def test_detects_sqlite_error(self, mock_fetch):
        mock_fetch.return_value = "SQLITE_ERROR: near 'test': syntax error"
        findings = sqli_test("http://example.com/page?id=1")
        assert len(findings) >= 1

    @patch("scanner._fetch")
    def test_no_findings_clean_response(self, mock_fetch):
        mock_fetch.return_value = "<html><body>Normal page</body></html>"
        findings = sqli_test("http://example.com/page?id=1")
        assert findings == []

    @patch("scanner._fetch")
    def test_no_params_returns_empty(self, mock_fetch):
        findings = sqli_test("http://example.com/page")
        assert findings == []
        mock_fetch.assert_not_called()

    @patch("scanner._fetch")
    def test_empty_response_no_findings(self, mock_fetch):
        mock_fetch.return_value = ""
        findings = sqli_test("http://example.com/page?id=1")
        assert findings == []

    @patch("scanner._fetch")
    def test_stops_after_first_finding_per_param(self, mock_fetch):
        """Once a finding is detected for a param, stop testing more payloads."""
        mock_fetch.return_value = "you have an error in your sql syntax"
        findings = sqli_test("http://example.com/page?id=1")
        # Should only have one finding per parameter
        assert len(findings) == 1

    @patch("scanner._fetch")
    def test_multiple_params(self, mock_fetch):
        """Each parameter should be tested independently."""
        mock_fetch.return_value = "you have an error in your sql syntax"
        findings = sqli_test("http://example.com/page?id=1&name=test")
        # Both params can have findings
        params_found = {f["param"] for f in findings}
        assert "id" in params_found
        assert "name" in params_found


# ---------------------------------------------------------------------------
# xss_test (mocked _fetch)
# ---------------------------------------------------------------------------


class TestXss:
    @patch("scanner._fetch")
    def test_detects_full_payload_reflection(self, mock_fetch):
        payload = f"<script>{XSS_MARKER}</script>"
        mock_fetch.return_value = f"<html>Your input: {payload}</html>"
        findings = xss_test("http://example.com/page?q=test")
        assert len(findings) >= 1
        assert findings[0]["type"] == "XSS"
        assert findings[0]["severity"] == "high"

    @patch("scanner._fetch")
    def test_detects_marker_only_reflection(self, mock_fetch):
        """Marker reflected but full payload escaped → medium severity."""
        mock_fetch.return_value = f"<html>Result: {XSS_MARKER}</html>"
        findings = xss_test("http://example.com/page?q=test")
        assert len(findings) >= 1
        xss_finding = findings[0]
        assert xss_finding["type"] == "XSS"
        # The marker-only finding could be medium
        assert xss_finding["severity"] in ("medium", "high")

    @patch("scanner._fetch")
    def test_no_reflection(self, mock_fetch):
        mock_fetch.return_value = "<html>No reflected content</html>"
        findings = xss_test("http://example.com/page?q=test")
        assert findings == []

    @patch("scanner._fetch")
    def test_no_params_returns_empty(self, mock_fetch):
        findings = xss_test("http://example.com/page")
        assert findings == []
        mock_fetch.assert_not_called()

    @patch("scanner._fetch")
    def test_empty_response(self, mock_fetch):
        mock_fetch.return_value = ""
        findings = xss_test("http://example.com/page?q=test")
        assert findings == []


# ---------------------------------------------------------------------------
# lfi_test (mocked _fetch)
# ---------------------------------------------------------------------------


class TestLfi:
    @patch("scanner._fetch")
    def test_detects_etc_passwd(self, mock_fetch):
        mock_fetch.return_value = "root:x:0:0:root:/root:/bin/bash"
        findings = lfi_test("http://example.com/page?file=test")
        assert len(findings) >= 1
        assert findings[0]["type"] == "LFI"
        assert findings[0]["severity"] == "critical"

    @patch("scanner._fetch")
    def test_detects_win_ini(self, mock_fetch):
        mock_fetch.return_value = "[fonts]\n; for 16-bit app support"
        findings = lfi_test("http://example.com/page?file=test")
        assert len(findings) >= 1
        assert findings[0]["type"] == "LFI"

    @patch("scanner._fetch")
    def test_detects_proc_environ(self, mock_fetch):
        mock_fetch.return_value = "DOCUMENT_ROOT=/var/www/html"
        findings = lfi_test("http://example.com/page?file=test")
        assert len(findings) >= 1

    @patch("scanner._fetch")
    def test_no_findings_normal_response(self, mock_fetch):
        mock_fetch.return_value = "<html>Normal page content</html>"
        findings = lfi_test("http://example.com/page?file=test")
        assert findings == []

    @patch("scanner._fetch")
    def test_no_params_returns_empty(self, mock_fetch):
        findings = lfi_test("http://example.com/page")
        assert findings == []

    @patch("scanner._fetch")
    def test_empty_response(self, mock_fetch):
        mock_fetch.return_value = ""
        findings = lfi_test("http://example.com/page?file=test")
        assert findings == []

    @patch("scanner._fetch")
    def test_stops_after_first_finding_per_param(self, mock_fetch):
        mock_fetch.return_value = "root:x:0:0:root:/root:/bin/bash"
        findings = lfi_test("http://example.com/page?file=test")
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# scan_url / scan_urls
# ---------------------------------------------------------------------------


class TestScanUrl:
    @patch("scanner._fetch")
    def test_combines_all_tests(self, mock_fetch):
        """scan_url runs SQLi, XSS, and LFI tests."""
        mock_fetch.return_value = "<html>Normal</html>"
        findings = scan_url("http://example.com/page?id=1")
        assert isinstance(findings, list)

    @patch("scanner._fetch")
    def test_no_params_empty(self, mock_fetch):
        findings = scan_url("http://example.com/page")
        assert findings == []

    @patch("scanner._fetch")
    def test_detects_multiple_vuln_types(self, mock_fetch):
        """If the response matches multiple patterns, we get multiple types."""
        mock_fetch.return_value = (
            f"you have an error in your sql syntax {XSS_MARKER} root:x:0:0:"
        )
        findings = scan_url("http://example.com/page?id=1")
        types = {f["type"] for f in findings}
        # Should detect at least SQLi and LFI
        assert "SQLi" in types
        assert "LFI" in types


class TestScanUrls:
    @patch("scanner._fetch")
    def test_scans_multiple_urls(self, mock_fetch):
        mock_fetch.return_value = "<html>Normal</html>"
        findings = scan_urls([
            "http://example.com/page?id=1",
            "http://example.com/other?name=x",
        ])
        assert isinstance(findings, list)

    @patch("scanner._fetch")
    def test_empty_list(self, mock_fetch):
        findings = scan_urls([])
        assert findings == []

    @patch("scanner._fetch")
    def test_exception_in_one_url_continues(self, mock_fetch):
        """If scanning one URL fails, continue with others."""
        mock_fetch.side_effect = [Exception("fail"), "<html>Normal</html>"]
        findings = scan_urls([
            "http://example.com/page?id=1",
            "http://example.com/other?name=x",
        ])
        # Should not crash, returns whatever was found
        assert isinstance(findings, list)


# ---------------------------------------------------------------------------
# Payload / pattern data integrity
# ---------------------------------------------------------------------------


class TestPayloadIntegrity:
    def test_sqli_payloads_not_empty(self):
        assert len(SQLI_PAYLOADS) > 0

    def test_sqli_error_patterns_not_empty(self):
        assert len(SQLI_ERROR_PATTERNS) > 0

    def test_xss_payloads_contain_marker(self):
        for payload in XSS_PAYLOADS:
            assert XSS_MARKER in payload

    def test_lfi_payloads_not_empty(self):
        assert len(LFI_PAYLOADS) > 0

    def test_lfi_success_patterns_not_empty(self):
        assert len(LFI_SUCCESS_PATTERNS) > 0

    def test_sqli_patterns_are_compiled_regex(self):
        import re
        for pattern in SQLI_ERROR_PATTERNS:
            assert isinstance(pattern, re.Pattern)

    def test_lfi_patterns_are_compiled_regex(self):
        import re
        for pattern in LFI_SUCCESS_PATTERNS:
            assert isinstance(pattern, re.Pattern)
