import os
import sys
import types
import importlib
import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_extract_text_missing_tesseract(monkeypatch):
    pytesseract_stub = types.SimpleNamespace(
        Output=types.SimpleNamespace(DICT={}),
        pytesseract=types.SimpleNamespace(tesseract_cmd=""),
        image_to_data=lambda *a, **k: {},
    )
    sys.modules["pytesseract"] = pytesseract_stub

    pil_module = types.ModuleType("PIL")
    class DummyImage:
        pass
    pil_module.Image = DummyImage
    sys.modules["PIL"] = pil_module

    sys.modules.pop("ocr", None)
    import ocr
    importlib.reload(ocr)

    def boom(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(ocr.pytesseract, "image_to_data", boom)
    with pytest.raises(RuntimeError) as excinfo:
        ocr.extract_text(ocr.Image())
    assert "Tesseract binary not found" in str(excinfo.value)
