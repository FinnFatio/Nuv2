from __future__ import annotations

from typing import Any, Callable, Dict

# Global registry mapping tool name to metadata and callable
REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_tool(
    *,
    name: str,
    version: str,
    summary: str,
    safety: str,
    timeout_ms: int,
    rate_limit_per_min: int,
    enabled_in_safe_mode: bool,
    func: Callable[..., Any],
) -> None:
    REGISTRY[name] = {
        "name": name,
        "version": version,
        "summary": summary,
        "safety": safety,
        "timeout_ms": timeout_ms,
        "rate_limit_per_min": rate_limit_per_min,
        "enabled_in_safe_mode": enabled_in_safe_mode,
        "func": func,
    }


def get_tool(name: str) -> Dict[str, Any] | None:
    return REGISTRY.get(name)


def clear() -> None:
    REGISTRY.clear()
