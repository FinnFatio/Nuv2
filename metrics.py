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
_policy_blocked: Counter[str] = Counter()
_tool_calls: Counter[Tuple[str, str]] = Counter()
_tool_latency: Dict[str, Deque[int]] = {}


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


def record_policy_block(reason: str) -> None:
    _policy_blocked[reason] += 1


def record_tool_call(name: str, outcome: str, elapsed_ms: int) -> None:
    _tool_calls[(name, outcome)] += 1
    _tool_latency.setdefault(name, deque(maxlen=_WINDOW)).append(int(elapsed_ms))


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
    tool_latency = {
        name: {"p50": _percentile(dq, 50), "p95": _percentile(dq, 95)}
        for name, dq in _tool_latency.items()
    }
    tool_calls: Dict[str, Dict[str, int]] = {}
    for (name, outcome), count in _tool_calls.items():
        tool_calls.setdefault(name, {})[outcome] = count
    return {
        "latency_ms": latency,
        "fallbacks": dict(_fallbacks),
        "error_rate": error_rate,
        "status_total": status_total,
        "rate_limited_total": _rate_limited_total,
        "resets_total": _fallbacks.get("resets", 0),
        "gauges": dict(_gauges),
        "enums": {k: dict(v) for k, v in _enums.items()},
        "policy_blocked_total": dict(_policy_blocked),
        "tool_calls_total": tool_calls,
        "tool_latency_ms": tool_latency,
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
    _policy_blocked.clear()
    _tool_calls.clear()
    _tool_latency.clear()
