from typing import Dict
from cursor import get_position
from screenshot import capture_around
from uia import get_element_info
from ocr import extract_text

UIA_THRESHOLD = 0.7


def describe_under_cursor() -> Dict:
    pos = get_position()
    app, element, uia_text, uia_conf = get_element_info(pos["x"], pos["y"])
    img, _ = capture_around(pos)
    ocr_text, ocr_conf = extract_text(img)
    chosen = uia_text if uia_conf >= UIA_THRESHOLD else ocr_text
    return {
        "cursor": pos,
        "app": app,
        "element": element,
        "text": {"uia": uia_text, "ocr": ocr_text, "chosen": chosen},
        "confidence": {"uia": uia_conf, "ocr": ocr_conf},
    }
