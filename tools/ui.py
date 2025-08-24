from __future__ import annotations

from typing import Any, Dict

from cursor import get_position

try:  # pragma: no cover - optional dependency
    import pygetwindow as gw  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - missing optional dep
    gw = None

try:  # pragma: no cover - optional dependency
    import win32process  # type: ignore[import-untyped]
    import psutil  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - missing optional dep
    win32process = None
    psutil = None

try:  # pragma: no cover - optional dependency
    from uia import get_element_info  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - missing optional dep
    get_element_info = None


def what_under_mouse() -> Dict[str, Any]:
    pos = get_position()
    window: Dict[str, Any] | None = None
    if gw is not None:
        try:
            w = gw.getActiveWindow()
            if w is not None:
                title = getattr(w, "title", "") or ""
                app = ""
                if win32process and psutil:
                    try:
                        _tid, pid = win32process.GetWindowThreadProcessId(getattr(w, "_hWnd"))
                        app = psutil.Process(pid).name()
                    except Exception:
                        app = ""
                window = {"title": title, "app": app}
        except Exception:
            window = None

    control: Dict[str, Any] | None = None
    if get_element_info is not None:
        try:
            _, element, _, _ = get_element_info(pos["x"], pos["y"])
            role = element.get("role") or element.get("control_type") or ""
            name = element.get("name") or ""
            if role or name:
                control = {"role": role, "name": name}
        except Exception:
            control = None

    return {"x": pos["x"], "y": pos["y"], "window": window, "control": control}


__all__ = ["what_under_mouse"]

