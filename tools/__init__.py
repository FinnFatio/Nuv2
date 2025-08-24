from __future__ import annotations

from registry import register_tool
from . import system, fs, archive, web, ui

__all__ = ["register_all_tools"]


def register_all_tools() -> None:
    register_tool(
        name="system.capture_screen",
        version="1",
        summary="capture screen region",
        safety="read",
        timeout_ms=5000,
        rate_limit_per_min=30,
        enabled_in_safe_mode=True,
        func=system.capture_screen,
    )
    register_tool(
        name="system.ocr",
        version="1",
        summary="ocr screen region",
        safety="read",
        timeout_ms=5000,
        rate_limit_per_min=30,
        enabled_in_safe_mode=True,
        func=system.ocr,
    )
    register_tool(
        name="system.uia_query",
        version="1",
        summary="uia query",
        safety="read",
        timeout_ms=5000,
        rate_limit_per_min=30,
        enabled_in_safe_mode=True,
        func=system.uia_query,
    )
    register_tool(
        name="system.info",
        version="1",
        summary="basic system info",
        safety="read",
        timeout_ms=1000,
        rate_limit_per_min=60,
        enabled_in_safe_mode=True,
        func=system.info,
    )
    register_tool(
        name="fs.list",
        version="1",
        summary="list directory",
        safety="read",
        timeout_ms=1000,
        rate_limit_per_min=60,
        enabled_in_safe_mode=True,
        func=fs.list,
    )
    register_tool(
        name="fs.read",
        version="1",
        summary="read file",
        safety="read",
        timeout_ms=1000,
        rate_limit_per_min=60,
        enabled_in_safe_mode=True,
        func=fs.read,
    )
    register_tool(
        name="archive.list",
        version="1",
        summary="list archive entries",
        safety="read",
        timeout_ms=1000,
        rate_limit_per_min=60,
        enabled_in_safe_mode=True,
        func=archive.list,
    )
    register_tool(
        name="archive.read",
        version="1",
        summary="read archive entry",
        safety="read",
        timeout_ms=1000,
        rate_limit_per_min=60,
        enabled_in_safe_mode=True,
        func=archive.read,
    )
    register_tool(
        name="web.read",
        version="1",
        summary="read web page",
        safety="read",
        timeout_ms=5000,
        rate_limit_per_min=30,
        enabled_in_safe_mode=True,
        func=web.read,
    )
    register_tool(
        name="ui.what_under_mouse",
        version="1",
        summary="cursor position and UI element",
        safety="read",
        timeout_ms=1000,
        rate_limit_per_min=60,
        enabled_in_safe_mode=True,
        func=ui.what_under_mouse,
        schema={
            "args": {"type": "object", "properties": {}},
            "returns": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "window": {
                        "type": ["object", "null"],
                        "properties": {
                            "title": {"type": "string"},
                            "app": {"type": "string"},
                        },
                    },
                    "control": {
                        "type": ["object", "null"],
                        "properties": {
                            "role": {"type": "string"},
                            "name": {"type": "string"},
                        },
                    },
                },
            },
        },
    )
