import json
import sys
from PIL import Image
import pytest

import inspect_point
import resolve


def test_inspect_point_tesseract_error(monkeypatch, capsys):
    def fake_get_position():
        return {"x": 0, "y": 0}

    def fake_element_info(x, y):
        return ({}, {"bounds": {}}, "", 0.0)

    def fake_capture_around(pos, bounds=None):
        return (Image.new("RGB", (1, 1)), None)

    def raise_ocr(img):
        raise RuntimeError("tesseract_failed")

    monkeypatch.setattr(resolve, "get_position", fake_get_position)
    monkeypatch.setattr(resolve, "get_element_info", fake_element_info)
    monkeypatch.setattr(resolve, "capture_around", fake_capture_around)
    monkeypatch.setattr(resolve, "extract_text", raise_ocr)
    monkeypatch.setattr(sys, "argv", ["inspect_point.py"])
    with pytest.raises(SystemExit) as exc:
        inspect_point.main()
    assert exc.value.code == 0
    data = json.loads(capsys.readouterr().out.strip())
    assert data["data"]["errors"]["extract_text"] == "tesseract_failed"
