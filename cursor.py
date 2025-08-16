import ctypes
from typing import Dict

class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_position() -> Dict[str, int]:
    """Return current cursor position as a dict with x and y."""
    pt = _POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return {"x": pt.x, "y": pt.y}
