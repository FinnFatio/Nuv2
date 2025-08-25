from __future__ import annotations

from typing import Dict, Any


def what_under_mouse() -> Dict[str, Any]:
    try:
        from cursor import get_position
    except Exception:
        return {
            "kind": "error",
            "code": "missing_dep",
            "message": "cursor dependency missing",
            "hint": "",
        }
    try:
        pos = get_position()
    except Exception:
        return {
            "kind": "error",
            "code": "missing_dep",
            "message": "cursor position unavailable",
            "hint": "",
        }
    x, y = pos["x"], pos["y"]
    window = None
    try:
        import pygetwindow as gw
        w = None
        if hasattr(gw, "getWindowsAt"):
            ws = gw.getWindowsAt(x, y)
            if ws:
                w = ws[0]
        if w is None:
            w = gw.getActiveWindow()
        if w is not None:
            title = getattr(w, "title", "") or ""
            app = getattr(w, "title", "") or ""
            window = {"title": title, "app": app}
    except Exception:
        window = None
    control = None
    try:
        from uia import get_element_info

        _, elem, _, _ = get_element_info(x, y)
        role = elem.get("role") or elem.get("control_type") or ""
        name = elem.get("name") or ""
        if role or name:
            control = {"role": role, "name": name}
    except Exception:
        control = None
    return {"kind": "ok", "result": {"x": x, "y": y, "window": window, "control": control}}


__all__ = ["what_under_mouse"]
