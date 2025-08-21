from __future__ import annotations

from typing import Any, Dict, Tuple
from PIL.Image import Image as PILImage
import pytesseract
from logger import log_call
from settings import OCR_LANG, OCR_CFG, TESSERACT_CMD
from pathlib import Path
import shutil
import os


_tesseract_checked = False


def _ensure_tesseract() -> None:
    """Ensure the Tesseract binary is available and configured."""
    global _tesseract_checked
    if _tesseract_checked:
        return
    if TESSERACT_CMD:
        cmd = Path(TESSERACT_CMD)
        if cmd.is_file() and os.access(cmd, os.X_OK):
            pytesseract.pytesseract.tesseract_cmd = str(cmd)
        elif shutil.which(str(cmd)):
            pytesseract.pytesseract.tesseract_cmd = str(cmd)
        else:
            raise RuntimeError("tesseract_missing")
    _tesseract_checked = True


@log_call
def extract_text(image: PILImage) -> Tuple[str, float]:
    """Run OCR on the given image, returning text and confidence."""
    _ensure_tesseract()
    try:
        data: Dict[str, Any] = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            lang=OCR_LANG,
            config=OCR_CFG,
        )
    except FileNotFoundError as e:
        raise RuntimeError("tesseract_missing") from e
    except pytesseract.TesseractError as e:
        raise RuntimeError("tesseract_failed") from e
    words = [w for w in data["text"] if w.strip()]
    confidences = [float(c) for c in data["conf"] if c != "-1"]
    text = " ".join(words).strip()
    confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    return text, confidence
