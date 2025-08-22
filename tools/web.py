from __future__ import annotations

from urllib.parse import urlparse
import ipaddress
import socket
import requests

PRIVATE_NETS = [
    ipaddress.ip_network(n)
    for n in (
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "0.0.0.0/8",
        "::1/128",
        "fc00::/7",
    )
]
MAX_BYTES = 1024 * 1024  # 1 MB


def _is_private(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    for *_, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if any(ip in net for net in PRIVATE_NETS):
            return True
    return False


def read(url: str) -> dict:
    u = urlparse(url)
    if u.scheme not in ("http", "https"):
        raise ValueError("unsupported_scheme")
    if u.username or u.password:
        raise ValueError("blocked_userinfo")
    host = u.hostname or ""
    if host == "localhost" or _is_private(host):
        raise ValueError("blocked_host")
    s = requests.Session()
    s.trust_env = False  # ignore proxy settings from the environment
    resp = s.get(url, timeout=4, allow_redirects=True)
    if len(resp.history) > 3:
        raise ValueError("too_many_redirects")
    resp.raise_for_status()
    ct = resp.headers.get("content-type", "").lower()
    if not ct.startswith("text/"):
        raise ValueError("unsupported_content_type")
    content = resp.content
    if len(content) > MAX_BYTES:
        raise ValueError("too_large")
    return {
        "title": resp.headers.get("x-title", ""),
        "text": content.decode("utf-8", "ignore"),
    }
