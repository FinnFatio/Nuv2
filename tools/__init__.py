from __future__ import annotations

from registry import register_tool, REGISTRY
from . import system, fs, archive, web, ui, image

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
        schema={"args": {"type": "object", "properties": {"bounds": {"type": "object"}}},
                 "returns": {"type": "object", "properties": {"png_base64": {"type": "string"}}}},
    )
    register_tool(
        name="system.ocr",
        version="1",
        summary="ocr image or screen region",
        safety="read",
        timeout_ms=5000,
        rate_limit_per_min=30,
        enabled_in_safe_mode=True,
        func=system.ocr,
        schema={
            "args": {
                "type": "object",
                "properties": {
                    "bounds": {"type": "object"},
                    "path": {"type": "string"},
                    "png_base64": {"type": "string"},
                },
            },
            "returns": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            },
        },
    )
    register_tool(
        name="system.toolspec",
        version="1",
        summary="list available tools and schemas",
        safety="read",
        timeout_ms=1000,
        rate_limit_per_min=10,
        enabled_in_safe_mode=True,
        func=system.toolspec,
        schema={"args": {"type": "object", "properties": {}}, "returns": {"type": "object"}},
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
        schema={
            "args": {"type": "object", "properties": {}},
            "returns": {"type": "object"},
            "x-retry": 2,
        },
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
        schema={
            "args": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "recursive": {"type": "boolean"},
                },
            },
            "returns": {"type": "array", "items": {"type": "string"}},
        },
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
        schema={"args": {"type": "object", "properties": {"path": {"type": "string"}}},
                 "returns": {"type": "string"}},
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
        schema={"args": {"type": "object", "properties": {"path": {"type": "string"}}},
                 "returns": {"type": "array", "items": {"type": "string"}}},
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
        schema={"args": {"type": "object", "properties": {"path": {"type": "string"}, "inner_path": {"type": "string"}}},
                 "returns": {"type": "object", "properties": {"bytes_b64": {"type": "string"}}}},
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
        schema={"args": {"type": "object", "properties": {"url": {"type": "string"}}},
                 "returns": {"type": "object", "properties": {"text": {"type": "string"}, "url_final": {"type": "string"}}}},
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
                        "properties": {"title": {"type": "string"}, "app": {"type": "string"}},
                    },
                    "control": {
                        "type": ["object", "null"],
                        "properties": {"role": {"type": "string"}, "name": {"type": "string"}},
                    },
                },
            },
        },
    )
    register_tool(
        name="image.crop",
        version="1",
        summary="crop image region",
        safety="read",
        timeout_ms=1000,
        rate_limit_per_min=30,
        enabled_in_safe_mode=True,
        func=image.crop,
        schema={
            "args": {
                "type": "object",
                "properties": {
                    "png_base64": {"type": "string"},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "w": {"type": "integer"},
                    "h": {"type": "integer"},
                },
            },
            "returns": {"type": "object", "properties": {"png_base64": {"type": "string"}}},
        },
    )
    try:
        import metrics

        metrics.record_gauge("agent_tool_name_total", len(REGISTRY))
    except Exception:
        pass
