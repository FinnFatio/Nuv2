"""Utilities for retrieving UI Automation element information."""

from typing import Dict, Tuple, List
import psutil

try:  # pragma: no cover - optional on non-Windows platforms
    from pywinauto.uia_element_info import UIAElementInfo as PUIAElementInfo
    from pywinauto import uia_defines
except Exception:  # pragma: no cover - pywinauto may be unavailable
    PUIAElementInfo = None  # type: ignore
    uia_defines = None  # type: ignore

from logger import log_call


@log_call
def get_element_info(x: int, y: int) -> Tuple[Dict, Dict, str, float]:
    """Return window info, element info, text and confidence for position.

    The element dictionary contains UIA properties, supported patterns,
    derived affordances and the ancestor chain with opaque IDs.
    """

    if PUIAElementInfo is None:  # pragma: no cover - pywinauto missing
        return (
            {
                "handle": None,
                "active": None,
                "pid": None,
                "title": None,
                "app_path": None,
                "bounds": None,
            },
            {
                "control_type": None,
                "automation_id": None,
                "name": None,
                "value": None,
                "role": None,
                "is_enabled": None,
                "is_offscreen": None,
                "bounds": None,
                "patterns": [],
                "affordances": {},
                "ancestors": [],
            },
            "",
            0.0,
        )

    try:
        info = PUIAElementInfo.from_point((x, y))
    except Exception:
        return (
            {
                "handle": None,
                "active": None,
                "pid": None,
                "title": None,
                "app_path": None,
                "bounds": None,
            },
            {
                "control_type": None,
                "automation_id": None,
                "name": None,
                "value": None,
                "role": None,
                "is_enabled": None,
                "is_offscreen": None,
                "bounds": None,
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
        app_path = proc.exe()
    except Exception:
        app_path = None

    window = info.get_top_level_parent()
    window_bounds = None
    handle = None
    active = None
    title = ""
    if window is not None:
        title = window.name or ""
        handle = getattr(window, "handle", None)
        try:
            active = bool(window.element.CurrentHasKeyboardFocus)
        except Exception:
            active = None
        try:
            window_bounds = {
                "left": window.rectangle.left,
                "top": window.rectangle.top,
                "right": window.rectangle.right,
                "bottom": window.rectangle.bottom,
            }
        except Exception:
            window_bounds = None

    control_type = getattr(info, "control_type", None)
    automation_id = getattr(info, "automation_id", None)
    name = info.name or ""
    role = getattr(info, "localized_control_type", None)
    try:
        value = info.element.CurrentValue  # type: ignore[attr-defined]
    except Exception:
        try:
            value = info.element.GetCurrentPropertyValue(
                30045
            )  # LegacyIAccessibleValue
        except Exception:
            value = ""
    if value is None:
        value = ""
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
                "automation_id": getattr(current, "automation_id", "") or "",
            }
        )
        counter += 1
        try:
            parent = current.get_parent()
        except Exception:
            parent = None
        current = parent
    ancestors.reverse()

    window_info = {
        "handle": handle,
        "active": active,
        "pid": pid,
        "title": title,
        "app_path": app_path,
        "bounds": window_bounds,
    }
    element_info = {
        "control_type": control_type,
        "bounds": bounds,
        "automation_id": automation_id,
        "name": name,
        "role": role,
        "value": value,
        "is_enabled": is_enabled,
        "is_offscreen": is_offscreen,
        "patterns": patterns,
        "affordances": affordances,
        "ancestors": ancestors,
    }

    text = value if value else name
    conf = 1.0 if text else 0.0
    return window_info, element_info, text, conf
