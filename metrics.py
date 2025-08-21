from __future__ import annotations

from collections import Counter, deque
from typing import Deque, Dict, Tuple

_WINDOW = 100

_times: Dict[str, Deque[int]] = {
    "cursor": deque(maxlen=_WINDOW),
    "uia": deque(maxlen=_WINDOW),
    "capture": deque(maxlen=_WINDOW),
    "ocr": deque(maxlen=_WINDOW),
}
_fallbacks: Counter[str] = Counter()
_route_total: Counter[str] = Counter()
_route_errors: Counter[str] = Counter()
_route_status: Counter[Tuple[str, int]] = Counter()
_rate_limited_total = 0
_gauges: Dict[str, int | float] = {}
_enums: Dict[str, Counter[str]] = {}


def record_time(kind: str, elapsed_ms: int) -> None:
    dq = _times.get(kind)
    if dq is not None:
        dq.append(int(elapsed_ms))


def record_fallback(name: str) -> None:
    _fallbacks[name] += 1


def record_gauge(name: str, value: int | float) -> None:
    _gauges[name] = value


def record_enum(name: str, value: str) -> None:
    _enums.setdefault(name, Counter())[value] += 1


def record_request(route: str, status: int) -> None:
    global _rate_limited_total
    _route_total[route] += 1
    if status >= 400:
        _route_errors[route] += 1
    _route_status[(route, status)] += 1
    if status == 429:
        _rate_limited_total += 1


def _percentile(dq: Deque[int], pct: float) -> int | None:
    if not dq:
        return None
    data = sorted(dq)
    k = int(len(data) * pct / 100)
    if k >= len(data):
        k = len(data) - 1
    return data[k]


def summary() -> Dict:
    latency = {
        kind: {
            "p50": _percentile(dq, 50),
            "p95": _percentile(dq, 95),
        }
        for kind, dq in _times.items()
    }
    error_rate = {
        route: (_route_errors[route] / total if total else 0.0)
        for route, total in _route_total.items()
    }
    status_total: Dict[str, Dict[int, int]] = {}
    for (route, status), count in _route_status.items():
        status_total.setdefault(route, {})[status] = count
    return {
        "latency_ms": latency,
        "fallbacks": dict(_fallbacks),
        "error_rate": error_rate,
        "status_total": status_total,
        "rate_limited_total": _rate_limited_total,
        "resets_total": _fallbacks.get("resets", 0),
        "gauges": dict(_gauges),
        "enums": {k: dict(v) for k, v in _enums.items()},
    }


def reset() -> None:
    for dq in _times.values():
        dq.clear()
    _fallbacks.clear()
    _route_total.clear()
    _route_errors.clear()
    _route_status.clear()
    _gauges.clear()
    _enums.clear()
    global _rate_limited_total
    _rate_limited_total = 0
