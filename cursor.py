import ctypes
from typing import Dict

from logger import log_call


# Try to make process DPI aware on Windows. This is a no-op on other systems.
try:  # pragma: no cover - platform specific best-effort
    _windll = ctypes.windll  # type: ignore[attr-defined]
    try:
        # Windows 8.1+ Per-Monitor DPI awareness
        _windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        # Fallback for Windows < 8.1
        _windll.user32.SetProcessDPIAware()
except Exception:  # pragma: no cover - non-Windows platforms
    _windll = None


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


@log_call
def get_position() -> Dict[str, int]:
    """Return current cursor position as a dict with x and y."""
    if _windll is None:  # pragma: no cover - executed only on non-Windows
        raise OSError("Cursor position is only supported on Windows")
    pt = _POINT()
    _windll.user32.GetCursorPos(ctypes.byref(pt))
    return {"x": pt.x, "y": pt.y}
