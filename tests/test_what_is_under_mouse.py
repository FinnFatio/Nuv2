import json
import sys
import types

import pytest


# Stub heavy dependencies before importing application modules
sys.modules["mss"] = types.SimpleNamespace()
pil_module = types.ModuleType("PIL")
image_module = types.ModuleType("PIL.Image")
image_module.Image = object
pil_module.Image = image_module
sys.modules["PIL"] = pil_module
sys.modules["PIL.Image"] = image_module
sys.modules["pytesseract"] = types.SimpleNamespace(
    Output=types.SimpleNamespace(DICT={}),
    pytesseract=types.SimpleNamespace(tesseract_cmd=""),
)
sys.modules["psutil"] = types.SimpleNamespace(Process=lambda pid: None)


import resolve
import what_is_under_mouse


def test_main_reports_tesseract_error(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise RuntimeError("tesseract_failed")

    # ensure our patched function is used
    monkeypatch.setattr(resolve, "describe_under_cursor", boom)
    monkeypatch.setattr(what_is_under_mouse, "describe_under_cursor", boom)
    monkeypatch.setattr(what_is_under_mouse, "setup", lambda *a, **k: None)

    with pytest.raises(SystemExit) as exc:
        what_is_under_mouse.main([])

    assert exc.value.code == 1
    data = json.loads(capsys.readouterr().out.strip())
    assert data["error"]["code"] == "tesseract_failed"
    assert data["error"]["message"] == "tesseract_failed"

