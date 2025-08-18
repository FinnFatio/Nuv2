import os
import sys
import types

# Stub out dependencies before importing resolve
sys.modules["mss"] = types.SimpleNamespace()
pil_module = types.ModuleType("PIL")
pil_module.Image = object
sys.modules["PIL"] = pil_module
sys.modules["pytesseract"] = types.SimpleNamespace(
    Output=types.SimpleNamespace(DICT={}),
    pytesseract=types.SimpleNamespace(tesseract_cmd=""),
)
sys.modules["psutil"] = types.SimpleNamespace(Process=lambda pid: None)

# Ensure resolve module can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import resolve


def test_describe_prefers_uia_when_visible(monkeypatch):
    monkeypatch.setattr(resolve, "get_position", lambda: {"x": 10, "y": 10})
    app = {}
    element = {"bounds": {"left": 0, "top": 0, "right": 100, "bottom": 100}, "is_offscreen": False}
    monkeypatch.setattr(resolve, "get_element_info", lambda x, y: (app, element, "uia_text", 0.9))
    monkeypatch.setattr(resolve, "capture_around", lambda pos, bounds=None: ("img", (0, 0, 0, 0)))
    monkeypatch.setattr(resolve, "extract_text", lambda img: ("ocr_text", 0.5))
    result = resolve.describe_under_cursor()
    assert result["text"]["chosen"] == "uia_text"
    assert result["source"] == "uia"


def test_describe_prefers_ocr_when_offscreen(monkeypatch):
    monkeypatch.setattr(resolve, "get_position", lambda: {"x": 10, "y": 10})
    app = {}
    element = {"bounds": {"left": 0, "top": 0, "right": 100, "bottom": 100}, "is_offscreen": True}
    monkeypatch.setattr(resolve, "get_element_info", lambda x, y: (app, element, "uia_text", 0.9))
    monkeypatch.setattr(resolve, "capture_around", lambda pos, bounds=None: ("img", (0, 0, 0, 0)))
    monkeypatch.setattr(resolve, "extract_text", lambda img: ("ocr_text", 0.5))
    result = resolve.describe_under_cursor()
    assert result["text"]["chosen"] == "ocr_text"
    assert result["source"] == "ocr"
