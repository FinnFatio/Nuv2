from __future__ import annotations

import datetime as _dt
import re
from typing import Dict

import requests

from urllib.parse import urlparse
import ipaddress
import socket

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

MAX_BYTES = 1_000_000


def _sanitize(text: str) -> str:
    from agent_local import _redact, _truncate

    return _truncate(_redact(text))


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


def read(url: str) -> Dict:
    u = urlparse(url)
    if u.scheme not in ("http", "https"):
        return {"kind": "error", "code": "bad_args", "message": "unsupported_scheme", "hint": ""}
    if u.username or u.password:
        return {"kind": "error", "code": "bad_args", "message": "blocked_userinfo", "hint": ""}
    host = u.hostname or ""
    if host == "localhost" or _is_private(host):
        return {"kind": "error", "code": "bad_args", "message": "blocked_host", "hint": ""}
    try:
        s = requests.Session()
        s.trust_env = False
        resp = s.get(url, timeout=10, allow_redirects=True)
        if len(resp.history) > 3:
            return {"kind": "error", "code": "bad_args", "message": "too_many_redirects", "hint": ""}
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "").lower()
        if not ct.startswith("text/"):
            return {"kind": "error", "code": "bad_args", "message": "unsupported_content_type", "hint": ""}
        content = resp.text[:MAX_BYTES]
        content = re.sub(r"<script.*?>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<style.*?>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<[^>]+>", " ", content)
        return {
            "kind": "ok",
            "result": {
                "text": _sanitize(content.strip()),
                "url_final": resp.url,
                "fetched_at": _dt.datetime.utcnow().isoformat(),
            },
        }
    except requests.Timeout:
        return {
            "kind": "error",
            "code": "timeout",
            "message": "request timed out",
            "hint": "",
        }
    except requests.RequestException as e:
        return {"kind": "error", "code": "http_error", "message": str(e), "hint": ""}


__all__ = ["read"]
