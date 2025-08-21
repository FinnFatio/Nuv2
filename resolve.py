from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple
from primitives import Bounds, Point
import hashlib
import secrets
import time

from cursor import get_position
from screenshot import capture_around
from uia import get_element_info
from ocr import extract_text
from logger import log
import metrics
from settings import UIA_THRESHOLD


# Runtime salt used for stable ID generation
RUNTIME_SALT = secrets.token_hex(8)

# Global cache for last seen IDs
ID_CACHE: Dict[str, str | None] = {
    "last_window_id": None,
    "last_editable_control_id": None,
}


def _hash_components(pid: int, path: str) -> str:
    """Create a stable short hash for the given components."""
    data = f"{pid}|{path}|{RUNTIME_SALT}".encode()
    return hashlib.sha256(data).hexdigest()[:16]


def _compute_ids(window: Dict[str, Any], element: Dict[str, Any]) -> Tuple[str, str]:
    """Return stable window and control identifiers."""
    pid = int(window.get("pid") or 0)
    ancestors = element.get("ancestors") or []
    path_segments = [
        f"{a.get('control_type', '')}:{a.get('name', '')}" for a in ancestors
    ]
    control_path = "/" + "/".join(path_segments)
    window_index = max(
        (i for i, a in enumerate(ancestors) if a.get("control_type") == "Window"),
        default=-1,
    )
    if window_index >= 0:
        window_path = "/" + "/".join(path_segments[: window_index + 1])
    else:
        window_path = control_path
    window_id = _hash_components(pid, window_path)
    control_id = _hash_components(pid, control_path)
    return window_id, control_id


def _bounds_dict(b: Mapping[str, int | str]) -> Bounds:
    bounds: Bounds = {
        "left": int(b["left"]),
        "top": int(b["top"]),
        "right": int(b["right"]),
        "bottom": int(b["bottom"]),
    }
    if "monitor" in b:
        bounds["monitor"] = str(b["monitor"])
    return bounds


def describe_under_cursor(x: int | None = None, y: int | None = None) -> Dict[str, Any]:
    timings: Dict[str, Dict[str, float]] = {}
    errors: Dict[str, str] = {}

    if x is not None and y is not None:
        pos: Point = {"x": x, "y": y}
    else:
        # get_position
        start = time.time()
        log("get_position.start", start)
        try:
            pos = get_position()
            log("get_position.end", start)
        except Exception as e:  # pragma: no cover - defensive
            log("get_position.error", start, error=str(e))
            errors["get_position"] = str(e)
            pos = {"x": 0, "y": 0}
        timings["get_position"] = {"start": start, "end": time.time()}

    # get_element_info
    start = time.time()
    log("get_element_info.start", start)
    try:
        window, element, uia_text, uia_conf = get_element_info(pos["x"], pos["y"])
        log("get_element_info.end", start)
    except Exception as e:  # pragma: no cover - defensive
        log("get_element_info.error", start, error=str(e))
        errors["get_element_info"] = str(e)
        window, element, uia_text, uia_conf = {}, {}, "", 0.0
    timings["get_element_info"] = {"start": start, "end": time.time()}

    # capture_around
    start = time.time()
    log("capture_around.start", start)
    b = element.get("bounds") if isinstance(element, dict) else None
    if isinstance(b, Mapping) and {"left", "top", "right", "bottom"} <= b.keys():
        bounds: Bounds | None = _bounds_dict(b)
    else:
        bounds = None
    try:
        img, region = capture_around(pos, bounds=bounds)
        log("capture_around.end", start)
    except Exception as e:  # pragma: no cover - defensive
        log("capture_around.error", start, error=str(e))
        errors["capture_around"] = str(e)
        img = None
        region = (0, 0, 0, 0)
    timings["capture_around"] = {"start": start, "end": time.time()}

    # extract_text
    start = time.time()
    log("extract_text.start", start)
    if img is not None:
        try:
            crop = None
            if bounds is not None:
                crop = (
                    max(0, bounds["left"] - region[0]),
                    max(0, bounds["top"] - region[1]),
                    max(0, min(region[2], bounds["right"]) - region[0]),
                    max(0, min(region[3], bounds["bottom"]) - region[1]),
                )
            ocr_text, ocr_conf = extract_text(img, region=crop)
            log("extract_text.end", start)
        except Exception as e:  # pragma: no cover - defensive
            log("extract_text.error", start, error=str(e))
            errors["extract_text"] = str(e)
            ocr_text, ocr_conf = "", 0.0
    else:
        log("extract_text.error", start, error="missing image")
        errors["extract_text"] = "missing image"
        ocr_text, ocr_conf = "", 0.0
    timings["extract_text"] = {"start": start, "end": time.time()}

    window_id, control_id = _compute_ids(window, element)
    window["window_id"] = window_id
    element["control_id"] = control_id
    ID_CACHE["last_window_id"] = window_id
    if element.get("affordances", {}).get("editable"):
        ID_CACHE["last_editable_control_id"] = control_id
    score = 0
    if element.get("is_offscreen") is False:
        score += 2
    if element.get("is_enabled"):
        score += 1
    if element.get("control_type") in {"Edit", "Text", "ListItem"}:
        score += 2
    if element.get("value"):
        score += 3
    name = element.get("name") or ""
    if len(name) >= 3:
        score += 1
    uia_ok = score >= UIA_THRESHOLD

    if uia_ok and (element.get("value") or name):
        chosen = element.get("value") or name
        source = "uia"
    else:
        chosen = ocr_text
        source = "ocr"
        metrics.record_fallback("used_ocr")

    # record metrics
    metric_key_map = {
        "get_position": "cursor",
        "get_element_info": "uia",
        "capture_around": "capture",
        "extract_text": "ocr",
    }
    for key, data in timings.items():
        elapsed = int((data["end"] - data["start"]) * 1000)
        metric_key = metric_key_map.get(key)
        if metric_key:
            metrics.record_time(metric_key, elapsed)
    metrics.record_gauge("text_len", len(chosen))
    metrics.record_enum("text_source", source)
    if source == "ocr":
        metrics.record_gauge("ocr_conf", ocr_conf)

    return {
        "cursor": pos,
        "window": window,
        "element": element,
        "text": {
            "uia": uia_text,
            "ocr": ocr_text,
            "chosen": chosen,
            "source": source,
        },
        "confidence": {"uia": uia_conf, "ocr": ocr_conf},
        "window_id": window_id,
        "control_id": control_id,
        "timings": timings,
        "errors": errors,
    }
