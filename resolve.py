from typing import Dict
from cursor import get_position
from screenshot import capture_around
from uia import get_element_info
from ocr import extract_text
from logger import log_call

UIA_THRESHOLD = 0.7


@log_call
def describe_under_cursor() -> Dict:
    pos = get_position()
    app, element, uia_text, uia_conf = get_element_info(pos["x"], pos["y"])
    bounds = element.get("bounds") if isinstance(element, dict) else None
    img, _ = capture_around(pos, bounds=bounds)
    ocr_text, ocr_conf = extract_text(img)
    visible = element.get("is_offscreen") is False if isinstance(element, dict) else False
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
    }
