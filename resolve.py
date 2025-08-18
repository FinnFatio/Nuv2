from typing import Dict, Tuple
import hashlib
import secrets

from cursor import get_position
from screenshot import capture_around
from uia import get_element_info
from ocr import extract_text
from logger import log_call

UIA_THRESHOLD = 0.7


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
def describe_under_cursor() -> Dict:
    pos = get_position()
    app, element, uia_text, uia_conf = get_element_info(pos["x"], pos["y"])
    bounds = element.get("bounds") if isinstance(element, dict) else None
    img, _ = capture_around(pos, bounds=bounds)
    ocr_text, ocr_conf = extract_text(img)
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
    return {
        "cursor": pos,
        "app": app,
        "element": element,
        "text": {"uia": uia_text, "ocr": ocr_text, "chosen": chosen},
        "confidence": {"uia": uia_conf, "ocr": ocr_conf},
        "source": source,
        "window_id": window_id,
        "control_id": control_id,
    }
