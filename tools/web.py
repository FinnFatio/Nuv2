from __future__ import annotations

from urllib.parse import urlparse
import ipaddress
import requests

PRIVATE_NETS = [
    ipaddress.ip_network(n)
    for n in (
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "::1/128",
        "fc00::/7",
    )
]
MAX_BYTES = 1024 * 1024  # 1 MB


def _is_private(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(ip in net for net in PRIVATE_NETS)


def read(url: str) -> dict:
    u = urlparse(url)
    if u.scheme not in ("http", "https"):
        raise ValueError("unsupported_scheme")
    host = u.hostname or ""
    if host == "localhost" or _is_private(host):
        raise ValueError("blocked_host")
    resp = requests.get(url, timeout=4, allow_redirects=True)
    if len(resp.history) > 3:
        raise ValueError("too_many_redirects")
    resp.raise_for_status()
    content = resp.content
    if len(content) > MAX_BYTES:
        raise ValueError("too_large")
    return {
        "title": resp.headers.get("x-title", ""),
        "text": content.decode("utf-8", "ignore"),
    }
