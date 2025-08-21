"""Utilities for retrieving UI Automation element information."""

from typing import Dict, Tuple, List
import psutil

try:  # pragma: no cover - optional on non-Windows platforms
    from pywinauto.uia_element_info import UIAElementInfo
    from pywinauto import uia_defines
except Exception:  # pragma: no cover - pywinauto may be unavailable
    UIAElementInfo = None  # type: ignore
    uia_defines = None  # type: ignore

from logger import log_call


@log_call
def get_element_info(x: int, y: int) -> Tuple[Dict, Dict, str, float]:
    """Return app info, element info, text and confidence for position.

    The element dictionary contains UIA properties, supported patterns,
    derived affordances and the ancestor chain with opaque IDs.
    """

    if UIAElementInfo is None:  # pragma: no cover - pywinauto missing
        return (
            {"pid": None, "exe": None, "window_title": None},
            {
                "control_type": None,
                "bounds": None,
                "automation_id": None,
                "name": None,
                "is_enabled": None,
                "is_offscreen": None,
                "patterns": [],
                "affordances": {},
                "ancestors": [],
            },
            "",
            0.0,
        )

    try:
        info = UIAElementInfo.from_point((x, y))
    except Exception:
        return (
            {"pid": None, "exe": None, "window_title": None},
            {
                "control_type": None,
                "bounds": None,
                "automation_id": None,
                "name": None,
                "is_enabled": None,
                "is_offscreen": None,
                "patterns": [],
                "affordances": {},
                "ancestors": [],
            },
            "",
            0.0,
        )

    bounds = {
        "left": info.rectangle.left,
        "top": info.rectangle.top,
        "right": info.rectangle.right,
        "bottom": info.rectangle.bottom,
    }

    pid = info.element.CurrentProcessId
    try:
        proc = psutil.Process(pid)
        exe = proc.name()
    except Exception:
        exe = None

    window = info.get_top_level_parent()
    window_title = window.name if window else ""

    control_type = getattr(info, "control_type", None)
    automation_id = getattr(info, "automation_id", None)
    name = info.name or ""
    try:
        is_enabled = info.element.CurrentIsEnabled
    except Exception:
        is_enabled = None
    try:
        is_offscreen = info.element.CurrentIsOffscreen
    except Exception:
        is_offscreen = None

    # Supported patterns
    pattern_ids: List[int] = []
    try:
        pattern_ids = list(info.element.GetSupportedPatternIds())
    except Exception:
        pattern_ids = []
    if uia_defines is not None:
        patterns = [
            uia_defines.pattern_id_to_name.get(pid, str(pid)) for pid in pattern_ids
        ]
    else:  # pragma: no cover - uia_defines absent
        patterns = [str(pid) for pid in pattern_ids]

    # Derive affordances
    pattern_set = set(patterns)
    affordances = {
        "editable": bool(pattern_set & {"ValuePattern", "TextPattern"}),
        "invokable": "InvokePattern" in pattern_set,
        "selectable": bool(pattern_set & {"SelectionPattern", "SelectionItemPattern"}),
    }

    # Build ancestor chain with opaque IDs
    ancestors: List[Dict[str, str]] = []
    current = info
    counter = 1
    while current is not None:
        ctype = getattr(current, "control_type", None)
        prefix = "W" if ctype == "Window" else "C"
        ancestors.append(
            {
                "id": f"{prefix}{counter}",
                "control_type": ctype or "",
                "name": current.name or "",
            }
        )
        counter += 1
        try:
            parent = current.get_parent()
        except Exception:
            parent = None
        current = parent
    ancestors.reverse()

    app = {"pid": pid, "exe": exe, "window_title": window_title}
    element = {
        "control_type": control_type,
        "bounds": bounds,
        "automation_id": automation_id,
        "name": name,
        "is_enabled": is_enabled,
        "is_offscreen": is_offscreen,
        "patterns": patterns,
        "affordances": affordances,
        "ancestors": ancestors,
    }

    conf = 1.0 if name else 0.0
    return app, element, name, conf
