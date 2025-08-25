from __future__ import annotations

import threading
import time
from typing import Any, Dict

import metrics
from registry import get_tool

# token bucket: name -> {"tokens": float, "last": float}
_RATE_LIMITS: Dict[str, Dict[str, float]] = {}

Envelope = Dict[str, Any]


def dispatch(
    request: Dict[str, Any], *, request_id: str, safe_mode: bool = False
) -> Envelope:
    """Dispatch a tool call described by request."""

    name = request.get("name")
    args = request.get("args", {}) or {}
    tool = get_tool(name)
    if tool is None:
        return {
            "kind": "error",
            "code": "not_found",
            "message": "tool not found",
            "hint": "",
        }

    start = time.time()
    if safe_mode and not tool["enabled_in_safe_mode"]:
        metrics.record_policy_block("safe_mode")
        metrics.record_tool_call(
            name or "", "forbidden", int((time.time() - start) * 1000)
        )
        return {
            "kind": "error",
            "code": "forbidden",
            "message": "disabled in safe mode",
            "hint": "",
        }

    now = time.time()
    rate = tool["rate_limit_per_min"]
    if rate:
        bucket = _RATE_LIMITS.setdefault(
            name, {"tokens": float(rate), "last": now}
        )
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(float(rate), bucket["tokens"] + elapsed * (rate / 60.0))
        bucket["last"] = now
        if bucket["tokens"] < 1.0:
            metrics.record_tool_call(
                name or "", "rate_limit", int((time.time() - start) * 1000)
            )
            metrics.record_route_status(name or "", "rate_limited")
            return {
                "kind": "error",
                "code": "rate_limit",
                "message": "rate limit exceeded",
                "hint": "",
            }
        bucket["tokens"] -= 1.0

    result: Any | None = None
    err: tuple[str, str] | None = None

    def target() -> None:
        nonlocal result, err
        try:
            result = tool["func"](**args)
        except TypeError as e:
            err = ("bad_args", str(e))
        except ValueError as e:
            err = ("bad_args", str(e))
        except Exception as e:  # pragma: no cover - defensive
            err = ("tool_error", str(e))

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(tool["timeout_ms"] / 1000)
    elapsed_ms = int((time.time() - start) * 1000)
    if thread.is_alive():
        metrics.record_tool_call(name or "", "timeout", elapsed_ms)
        return {
            "kind": "error",
            "code": "timeout",
            "message": "tool timed out",
            "hint": "",
            "elapsed_ms": elapsed_ms,
        }
    if err is not None:
        code, msg = err
        code = code or "internal"
        metrics.record_tool_call(name or "", "error", elapsed_ms)
        return {"kind": "error", "code": code, "message": msg, "hint": ""}

    metrics.record_tool_call(name or "", "ok", elapsed_ms)
    if isinstance(result, dict) and "kind" in result:
        return result
    return {"kind": "ok", "result": result}
