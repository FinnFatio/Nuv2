from typing import Tuple
from PIL import Image
import pytesseract
import os
import configparser


try:
    _tesseract_cmd = os.getenv("TESSERACT_CMD")
    if not _tesseract_cmd:
        cfg = configparser.ConfigParser()
        cfg.read("config.ini")
        _tesseract_cmd = cfg.get("tesseract", "tesseract_cmd", fallback=None)
    if _tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd
except Exception:
    pass


def extract_text(image: Image) -> Tuple[str, float]:
    """Run OCR on the given image, returning text and confidence."""
    try:
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            lang="por+eng",
            config="--oem 3 --psm 6",
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "Tesseract binary not found. Install Tesseract-OCR or set TESSERACT_CMD."
        ) from e
    words = [w for w in data["text"] if w.strip()]
    confidences = [float(c) for c in data["conf"] if c != "-1"]
    text = " ".join(words).strip()
    confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    return text, confidence
