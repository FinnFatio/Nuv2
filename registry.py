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
    schema: Dict[str, Any] | None = None,
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
    if schema is not None:
        REGISTRY[name]["schema"] = schema


def get_tool(name: str) -> Dict[str, Any] | None:
    return REGISTRY.get(name)


def register_alias(name: str, alias: str) -> None:
    if name in REGISTRY:
        REGISTRY[alias] = REGISTRY[name]


def clear() -> None:
    REGISTRY.clear()


def violates_policy(tool: Dict[str, Any], safe_mode: bool) -> bool:
    return safe_mode and tool.get("safety") == "destructive"


__all__ = [
    "register_tool",
    "get_tool",
    "register_alias",
    "clear",
    "violates_policy",
]
