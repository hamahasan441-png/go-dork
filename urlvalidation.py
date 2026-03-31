"""Shared URL validation utilities to prevent SSRF attacks."""

import ipaddress
import socket
from urllib.parse import urlparse


def is_safe_url(url: str) -> bool:
    """
    Check if a URL is safe to request (not targeting internal/private resources).

    Blocks requests to:
    - Loopback addresses (127.0.0.0/8, ::1)
    - Private network ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Link-local addresses (169.254.0.0/16)
    - Metadata service endpoints (e.g. cloud provider metadata at 169.254.169.254)

    Returns True if the URL is considered safe, False otherwise.
    """
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve hostname to IP(s) and check each one
        try:
            addr_infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            # Cannot resolve — allow the request (it will fail on its own)
            return True

        for family, _, _, _, sockaddr in addr_infos:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                return False

            if (
                ip.is_loopback
                or ip.is_private
                or ip.is_reserved
                or ip.is_link_local
                or ip.is_multicast
            ):
                return False

        return True
    except Exception:
        return False
