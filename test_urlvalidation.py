"""Tests for urlvalidation module — SSRF protection."""

import socket
from unittest.mock import patch

import pytest

from urlvalidation import is_safe_url


class TestIsSafeUrl:
    """Tests for the is_safe_url function."""

    # ------------------------------------------------------------------
    # Safe (public) URLs
    # ------------------------------------------------------------------

    def test_safe_public_http(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("93.184.216.34", 0)),
            ]
            assert is_safe_url("http://example.com") is True

    def test_safe_public_https(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("93.184.216.34", 0)),
            ]
            assert is_safe_url("https://example.com/path") is True

    def test_safe_public_with_port(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("93.184.216.34", 0)),
            ]
            assert is_safe_url("https://example.com:8443/api") is True

    # ------------------------------------------------------------------
    # Blocked — loopback addresses
    # ------------------------------------------------------------------

    def test_blocks_localhost(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("127.0.0.1", 0)),
            ]
            assert is_safe_url("http://localhost") is False

    def test_blocks_127_0_0_1(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("127.0.0.1", 0)),
            ]
            assert is_safe_url("http://127.0.0.1") is False

    def test_blocks_127_x(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("127.0.0.2", 0)),
            ]
            assert is_safe_url("http://127.0.0.2") is False

    def test_blocks_ipv6_loopback(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET6, 0, 0, "", ("::1", 0, 0, 0)),
            ]
            assert is_safe_url("http://[::1]") is False

    # ------------------------------------------------------------------
    # Blocked — private network ranges
    # ------------------------------------------------------------------

    def test_blocks_10_x(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("10.0.0.1", 0)),
            ]
            assert is_safe_url("http://10.0.0.1") is False

    def test_blocks_172_16_x(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("172.16.0.1", 0)),
            ]
            assert is_safe_url("http://172.16.0.1") is False

    def test_blocks_172_31_x(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("172.31.255.255", 0)),
            ]
            assert is_safe_url("http://172.31.255.255") is False

    def test_blocks_192_168_x(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("192.168.1.1", 0)),
            ]
            assert is_safe_url("http://192.168.1.1") is False

    # ------------------------------------------------------------------
    # Blocked — link-local & metadata
    # ------------------------------------------------------------------

    def test_blocks_link_local(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("169.254.1.1", 0)),
            ]
            assert is_safe_url("http://169.254.1.1") is False

    def test_blocks_cloud_metadata(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("169.254.169.254", 0)),
            ]
            assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False

    # ------------------------------------------------------------------
    # Blocked — multicast
    # ------------------------------------------------------------------

    def test_blocks_multicast(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("224.0.0.1", 0)),
            ]
            assert is_safe_url("http://224.0.0.1") is False

    # ------------------------------------------------------------------
    # Blocked — invalid scheme
    # ------------------------------------------------------------------

    def test_blocks_ftp_scheme(self):
        assert is_safe_url("ftp://example.com/file") is False

    def test_blocks_file_scheme(self):
        assert is_safe_url("file:///etc/passwd") is False

    def test_blocks_javascript_scheme(self):
        assert is_safe_url("javascript:alert(1)") is False

    def test_blocks_empty_scheme(self):
        assert is_safe_url("://example.com") is False

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_string(self):
        assert is_safe_url("") is False

    def test_no_hostname(self):
        assert is_safe_url("http://") is False

    def test_unresolvable_hostname_allowed(self):
        """If DNS resolution fails, the function allows the request."""
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.side_effect = socket.gaierror("Name not resolved")
            assert is_safe_url("http://nonexistent.invalid") is True

    def test_invalid_ip_in_resolution_blocked(self):
        """If getaddrinfo returns something ip_address can't parse, block."""
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("not-an-ip", 0)),
            ]
            assert is_safe_url("http://weird.host") is False

    def test_multiple_addresses_one_private(self):
        """If any resolved address is private, block the request."""
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("93.184.216.34", 0)),
                (socket.AF_INET, 0, 0, "", ("10.0.0.1", 0)),
            ]
            assert is_safe_url("http://dual.host") is False

    def test_multiple_addresses_all_safe(self):
        with patch("urlvalidation.socket.getaddrinfo") as mock_gai:
            mock_gai.return_value = [
                (socket.AF_INET, 0, 0, "", ("93.184.216.34", 0)),
                (socket.AF_INET, 0, 0, "", ("93.184.216.35", 0)),
            ]
            assert is_safe_url("http://cdn.example.com") is True
