from typing import Tuple
from PIL import Image
import pytesseract
from logger import log_call
from settings import OCR_LANG, OCR_CFG, TESSERACT_CMD
from pathlib import Path
import shutil


if TESSERACT_CMD:
    cmd = Path(TESSERACT_CMD)
    if cmd.is_file() or shutil.which(str(cmd)):
        pytesseract.pytesseract.tesseract_cmd = str(cmd)
    else:
        raise RuntimeError("tesseract_missing")


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
        raise RuntimeError("tesseract_missing") from e
    words = [w for w in data["text"] if w.strip()]
    confidences = [float(c) for c in data["conf"] if c != "-1"]
    text = " ".join(words).strip()
    confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    return text, confidence
