from __future__ import annotations

import base64
import io
import platform
import subprocess
from pathlib import Path
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


def ocr(
    bounds: Dict[str, int] | None = None,
    path: str | None = None,
    png_base64: str | None = None,
    image: bytes | None = None,
) -> Dict[str, Any]:
    """Run OCR on a screen region or image data.

    Accepts one of ``bounds`` (to capture the screen), ``path`` to an image
    file, ``png_base64`` with the image contents encoded or raw ``image``
    bytes.  The chosen input is converted to a PIL image before delegating to
    :func:`ocr.extract_text`.
    """

    try:
        from PIL import Image
    except Exception:
        return {
            "kind": "error",
            "code": "missing_dep",
            "message": "pillow not installed",
            "hint": "pip install -r requirements-optional.txt",
        }

    img = None
    if bounds is not None:
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
    else:
        try:
            if path is not None:
                data = Path(path).read_bytes()
            elif png_base64 is not None:
                data = base64.b64decode(png_base64)
            elif image is not None:
                data = image
            else:
                return {
                    "kind": "error",
                    "code": "missing_input",
                    "message": "path, png_base64 or image required",
                    "hint": "",
                }
            img = Image.open(io.BytesIO(data))
        except Exception as e:
            return {
                "kind": "error",
                "code": "bad_image",
                "message": str(e),
                "hint": "",
            }

    try:
        import ocr as ocr_lib

        text, conf = ocr_lib.extract_text(img)
    except RuntimeError as e:
        code = str(e)
        return {"kind": "error", "code": code, "message": code, "hint": ""}
    except Exception as e:
        return {
            "kind": "error",
            "code": "ocr_failed",
            "message": str(e),
            "hint": "",
        }
    return {
        "kind": "ok",
        "result": {"text": _sanitize(text), "confidence": conf},
    }


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


def toolspec() -> Dict[str, Any]:
    """Return a mapping of registered tools to their schemas."""
    try:
        from registry import REGISTRY

        specs = {name: t.get("schema") for name, t in REGISTRY.items()}
        return {"kind": "ok", "result": specs}
    except Exception as e:
        return {
            "kind": "error",
            "code": "toolspec_failed",
            "message": str(e),
            "hint": "",
        }


__all__ = ["capture_screen", "ocr", "info", "toolspec"]
