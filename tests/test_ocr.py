import os
import sys
from PIL import Image
import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ocr


def test_extract_text_passes_lang_and_cfg(monkeypatch):
    recorded = {}

    def fake_image_to_data(img, output_type, lang, config):
        recorded["lang"] = lang
        recorded["config"] = config
        return {"text": ["foo"], "conf": ["100"]}

    monkeypatch.setattr(ocr.pytesseract, "image_to_data", fake_image_to_data, raising=False)
    monkeypatch.setattr(ocr.pytesseract, "Output", type("O", (), {"DICT": None}), raising=False)
    img = Image.new("RGB", (10, 10))
    text, conf = ocr.extract_text(img)
    assert text == "foo"
    assert conf == 1.0
    assert recorded["lang"] == ocr.OCR_LANG
    assert recorded["config"] == ocr.OCR_CFG


def test_extract_text_missing_binary(monkeypatch):
    def raise_not_found(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(ocr.pytesseract, "image_to_data", raise_not_found, raising=False)
    monkeypatch.setattr(ocr.pytesseract, "Output", type("O", (), {"DICT": None}), raising=False)
    img = Image.new("RGB", (10, 10))
    with pytest.raises(RuntimeError) as exc:
        ocr.extract_text(img)
    assert "tesseract_missing" in str(exc.value)


def test_extract_text_tesseract_error(monkeypatch):
    class DummyError(Exception):
        pass

    def raise_error(*args, **kwargs):
        raise DummyError("oops")

    monkeypatch.setattr(ocr.pytesseract, "TesseractError", DummyError, raising=False)
    monkeypatch.setattr(ocr.pytesseract, "image_to_data", raise_error, raising=False)
    monkeypatch.setattr(ocr.pytesseract, "Output", type("O", (), {"DICT": None}), raising=False)
    img = Image.new("RGB", (10, 10))
    with pytest.raises(RuntimeError) as exc:
        ocr.extract_text(img)
    assert "tesseract_failed" in str(exc.value)


def test_invalid_tesseract_cmd(monkeypatch):
    import importlib
    import settings as settings_module

    monkeypatch.setenv("TESSERACT_CMD", "nonexistent")
    importlib.reload(settings_module)
    with pytest.raises(RuntimeError) as exc:
        importlib.reload(ocr)
    assert "tesseract_missing" in str(exc.value)
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    importlib.reload(settings_module)
    importlib.reload(ocr)
