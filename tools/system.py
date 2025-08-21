from __future__ import annotations

import base64
import io
from typing import Any, Dict, Tuple

from ocr import extract_text
from screenshot import capture
from resolve import describe_under_cursor


def _resolve_bounds(
    bounds: Dict[str, int] | None,
    window_id: str | None,
    control_id: str | None,
) -> Tuple[int, int, int, int] | None:
    if bounds:
        return (
            int(bounds["left"]),
            int(bounds["top"]),
            int(bounds["right"]),
            int(bounds["bottom"]),
        )
    if window_id or control_id:
        try:
            from api import BOUNDS_CACHE  # type: ignore
        except Exception:  # pragma: no cover - missing API context
            return None
        b = None
        if control_id:
            b = BOUNDS_CACHE.get(control_id)
        if b is None and window_id:
            b = BOUNDS_CACHE.get(window_id)
        if b is None:
            raise ValueError("id_not_found")
        return (b["left"], b["top"], b["right"], b["bottom"])
    return None


def capture_screen(
    bounds: Dict[str, int] | None = None,
    window_id: str | None = None,
    control_id: str | None = None,
) -> Dict[str, Any]:
    """Capture the screen and return PNG bytes as base64."""

    region = _resolve_bounds(bounds, window_id, control_id)
    img = capture(region)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"png_base64": data}


def ocr(
    bounds: Dict[str, int] | None = None,
    window_id: str | None = None,
    control_id: str | None = None,
) -> Dict[str, Any]:
    """Run OCR on the given region from the screen."""

    region = _resolve_bounds(bounds, window_id, control_id)
    if region is None:
        raise ValueError("missing_bounds")
    img = capture(region)
    text, conf = extract_text(img)
    return {"text": text, "confidence": conf}


def uia_query(x: int, y: int) -> Dict[str, Any]:
    """Query UIA/resolve for coordinates."""

    return describe_under_cursor(x, y)
