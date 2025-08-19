from typing import Tuple
from PIL import Image
import pytesseract
from logger import log_call
from settings import OCR_LANG, OCR_CFG, TESSERACT_CMD


try:
    if TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
except Exception:
    pass


@log_call
def extract_text(image: Image) -> Tuple[str, float]:
    """Run OCR on the given image, returning text and confidence."""
    try:
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            lang=OCR_LANG,
            config=OCR_CFG,
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
