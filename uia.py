from typing import Dict, Tuple
import psutil
from pywinauto.uia_element_info import UIAElementInfo
from logger import log_call


@log_call
def get_element_info(x: int, y: int) -> Tuple[Dict, Dict, str, float]:
    """Return app info, element info, text and confidence for position."""
    try:
        info = UIAElementInfo.from_point((x, y))
    except Exception:
        return ({"pid": None, "exe": None, "window_title": None},
                {"type": None, "bounds": None},
                "", 0.0)

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

    control_type = info.control_type
    name = info.name or ""
    conf = 1.0 if name else 0.0

    app = {"pid": pid, "exe": exe, "window_title": window_title}
    element = {"type": control_type, "bounds": bounds}
    return app, element, name, conf
