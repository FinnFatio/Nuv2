from typing import Dict, Tuple
import hashlib
import secrets
import time

from cursor import get_position
from screenshot import capture_around
from uia import get_element_info
from ocr import extract_text
from logger import log_call, log
import metrics
from settings import UIA_THRESHOLD


# Runtime salt used for stable ID generation
RUNTIME_SALT = secrets.token_hex(8)

# Global cache for last seen IDs
ID_CACHE = {"last_window_id": None, "last_editable_control_id": None}


def _hash_components(pid: int, path: str) -> str:
    """Create a stable short hash for the given components."""
    data = f"{pid}|{path}|{RUNTIME_SALT}".encode()
    return hashlib.sha256(data).hexdigest()[:16]


def _compute_ids(app: Dict, element: Dict) -> Tuple[str, str]:
    """Return stable window and control identifiers."""
    pid = app.get("pid")
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


@log_call
def describe_under_cursor(x: int | None = None, y: int | None = None) -> Dict:
    timings: Dict[str, Dict[str, float]] = {}
    errors: Dict[str, str] = {}

    if x is not None and y is not None:
        pos = {"x": x, "y": y}
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
        app, element, uia_text, uia_conf = get_element_info(pos["x"], pos["y"])
        log("get_element_info.end", start)
    except Exception as e:  # pragma: no cover - defensive
        log("get_element_info.error", start, error=str(e))
        errors["get_element_info"] = str(e)
        app, element, uia_text, uia_conf = {}, {}, "", 0.0
    timings["get_element_info"] = {"start": start, "end": time.time()}

    # capture_around
    start = time.time()
    log("capture_around.start", start)
    bounds = element.get("bounds") if isinstance(element, dict) else None
    try:
        img, _ = capture_around(pos, bounds=bounds)
        log("capture_around.end", start)
    except Exception as e:  # pragma: no cover - defensive
        log("capture_around.error", start, error=str(e))
        errors["capture_around"] = str(e)
        img = None
    timings["capture_around"] = {"start": start, "end": time.time()}

    # extract_text
    start = time.time()
    log("extract_text.start", start)
    if img is not None:
        try:
            ocr_text, ocr_conf = extract_text(img)
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

    visible = element.get("is_offscreen") is False if isinstance(element, dict) else False
    window_id, control_id = _compute_ids(app, element)
    app["window_id"] = window_id
    element["control_id"] = control_id
    ID_CACHE["last_window_id"] = window_id
    if element.get("affordances", {}).get("editable"):
        ID_CACHE["last_editable_control_id"] = control_id
    if uia_conf >= UIA_THRESHOLD and visible:
        chosen = uia_text
        source = "uia"
    else:
        chosen = ocr_text
        source = "ocr"
        metrics.record_fallback("used_ocr")
    return {
        "cursor": pos,
        "app": app,
        "element": element,
        "text": {"uia": uia_text, "ocr": ocr_text, "chosen": chosen},
        "confidence": {"uia": uia_conf, "ocr": ocr_conf},
        "source": source,
        "window_id": window_id,
        "control_id": control_id,
        "timings": timings,
        "errors": errors,
    }
