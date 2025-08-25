from __future__ import annotations

import base64
import io
import platform
import subprocess
from typing import Any, Dict, Tuple


# helpers ---------------------------------------------------------------


def _sanitize(text: str) -> str:
    from agent_local import _redact, _truncate  # lazy import to avoid cycles

    return _truncate(_redact(text))


def _grab(bounds: Tuple[int, int, int, int] | None) -> Any:
    """Return a PIL Image of the screen or raise RuntimeError('missing_dep')."""
    left = top = 0
    width = height = 0
    if bounds is not None:
        left, top, right, bottom = bounds
        width, height = right - left, bottom - top
    try:  # mss path
        import mss
        from PIL import Image

        with mss.mss() as sct:  # type: ignore[attr-defined]
            mon = {
                "left": left,
                "top": top,
                "width": width or sct.monitors[1]["width"],
                "height": height or sct.monitors[1]["height"],
            }
            shot = sct.grab(mon)
            return Image.frombytes("RGB", shot.size, shot.rgb)
    except Exception:
        try:  # fallback to ImageGrab
            from PIL import ImageGrab

            box = (left, top, left + (width or 0), top + (height or 0)) or None
            return ImageGrab.grab(box)
        except Exception as e:
            raise RuntimeError("missing_dep") from e


def capture(bounds: Tuple[int, int, int, int] | None = None) -> Any:
    return _grab(bounds)


# tools ----------------------------------------------------------------


def capture_screen(bounds: Dict[str, int] | None = None) -> Dict[str, Any]:
    try:
        b = None
        if bounds:
            b = (bounds["left"], bounds["top"], bounds["right"], bounds["bottom"])
        img = capture(b)
    except RuntimeError:
        return {
            "kind": "error",
            "code": "missing_dep",
            "message": "mss or pillow not available",
            "hint": "pip install -r requirements-optional.txt",
        }
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    png = _sanitize(data)
    truncated = False
    if len(png) > 1500:
        png = png[:1500]
        truncated = True
    result: Dict[str, Any] = {"png_base64": png}
    if truncated:
        result["truncated"] = True
    return {"kind": "ok", "result": result}


def ocr(bounds: Dict[str, int]) -> Dict[str, Any]:
    try:
        subprocess.run(["tesseract", "-v"], check=True, capture_output=True)
    except Exception:
        return {
            "kind": "error",
            "code": "missing_dep",
            "message": "tesseract not installed",
            "hint": "install tesseract and pytesseract",
        }
    try:
        import pytesseract
    except Exception:
        return {
            "kind": "error",
            "code": "missing_dep",
            "message": "pytesseract not installed",
            "hint": "pip install -r requirements-optional.txt",
        }
    try:
        img = capture(
            (bounds["left"], bounds["top"], bounds["right"], bounds["bottom"])
        )
    except RuntimeError:
        return {
            "kind": "error",
            "code": "missing_dep",
            "message": "mss or pillow not available",
            "hint": "pip install -r requirements-optional.txt",
        }
    text = pytesseract.image_to_string(img)
    return {"kind": "ok", "result": {"text": _sanitize(text)}}


def info() -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "os": {
            "name": platform.system(),
            "version": platform.release(),
        },
        "cpu": None,
        "ram_bytes": None,
        "gpus": None,
        "monitors": None,
        "safe_mode": None,
    }
    try:
        import psutil

        data["cpu"] = {"count": psutil.cpu_count(logical=True)}
        data["ram_bytes"] = psutil.virtual_memory().total
    except Exception:
        pass
    try:
        import torch

        if torch.cuda.is_available():
            data["gpus"] = [
                torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())
            ]
    except Exception:
        pass
    try:
        from screeninfo import get_monitors

        data["monitors"] = [
            {"width": m.width, "height": m.height} for m in get_monitors()
        ]
    except Exception:
        pass
    try:
        from settings import SAFE_MODE

        data["safe_mode"] = bool(SAFE_MODE)
    except Exception:
        data["safe_mode"] = None
    return {"kind": "ok", "result": data}


__all__ = ["capture_screen", "ocr", "info"]
