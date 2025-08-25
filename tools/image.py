from __future__ import annotations

import base64
import io
from typing import Dict, Any


def _sanitize(text: str) -> str:
    from agent_local import _redact, _truncate  # type: ignore

    return _truncate(_redact(text))


def crop(png_base64: str, x: int, y: int, w: int, h: int) -> Dict[str, Any]:
    try:
        from PIL import Image
    except Exception:
        return {
            "kind": "error",
            "code": "missing_dep",
            "message": "pillow not installed",
            "hint": "pip install -r requirements-optional.txt",
        }
    try:
        data = base64.b64decode(png_base64)
        img = Image.open(io.BytesIO(data))
        cropped = img.crop((x, y, x + w, y + h))
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        out = base64.b64encode(buf.getvalue()).decode("ascii")
        png = _sanitize(out)
        truncated = False
        if len(png) > 1500:
            png = png[:1500]
            truncated = True
        result: Dict[str, Any] = {"png_base64": png}
        if truncated:
            result["truncated"] = True
        return {"kind": "ok", "result": result}
    except Exception as e:
        return {
            "kind": "error",
            "code": "crop_failed",
            "message": str(e),
            "hint": "",
        }


__all__ = ["crop"]
