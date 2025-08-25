import sys
import types
import zipfile
from pathlib import Path

import pytest

from tools import register_all_tools, system, fs, archive, web, ui
from registry import REGISTRY, clear


def test_register_all_tools_idempotent():
    clear()
    register_all_tools()
    n = len(REGISTRY)
    register_all_tools()
    assert len(REGISTRY) == n


def test_capture_screen_missing_dep(monkeypatch):
    monkeypatch.setitem(sys.modules, "mss", None)
    monkeypatch.setitem(sys.modules, "PIL", None)
    res = system.capture_screen()
    assert res["kind"] == "error" and res["code"] == "missing_dep"


def test_capture_screen_ok(monkeypatch):
    class Img:
        def save(self, buf, format="PNG"):
            buf.write(b"fake")

    monkeypatch.setattr(system, "_grab", lambda b: Img())
    out = system.capture_screen()
    assert out["kind"] == "ok"


def test_ocr_missing_dep(monkeypatch):
    class Img:
        pass

    monkeypatch.setattr(system, "_grab", lambda b: Img())
    monkeypatch.setitem(
        sys.modules,
        "pytesseract",
        types.SimpleNamespace(image_to_string=lambda img: ""),
    )
    monkeypatch.setattr(
        system.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError())
    )
    res = system.ocr({"left": 0, "top": 0, "right": 1, "bottom": 1})
    assert res["code"] == "missing_dep"


def test_ocr_ok(monkeypatch):
    class Img: ...
    monkeypatch.setattr(system, "_grab", lambda b: Img())

    pyt = types.SimpleNamespace(image_to_string=lambda img: "hi")
    monkeypatch.setitem(sys.modules, "pytesseract", pyt)
    monkeypatch.setattr(system.subprocess, "run", lambda *a, **k: None)
    res = system.ocr({"left": 0, "top": 0, "right": 1, "bottom": 1})
    assert res["kind"] == "ok" and "text" in res["result"]


def test_fs_allowlist(tmp_path):
    p = Path.cwd() / "tmp_allow"
    p.mkdir(exist_ok=True)
    f = p / "a.txt"
    f.write_text("hello")
    assert fs.list(str(p))["kind"] == "ok"
    assert fs.read(str(f))["kind"] == "ok"
    bad = tmp_path / "bad.txt"
    bad.write_text("x")
    assert fs.read(str(bad))["code"] == "forbidden_path"


def test_archive_list_read(tmp_path):
    p = Path.cwd() / "arc.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("x.txt", "hi")
    assert archive.list(str(p))["kind"] == "ok"
    assert archive.read(str(p), "x.txt")["kind"] == "ok"
    p.unlink()


def test_web_read_sanitize(monkeypatch):
    class Resp:
        url = "http://a"
        history = []
        headers = {"content-type": "text/html"}
        text = "<h1>hi</h1><script>bad()</script>"

        def raise_for_status(self):
            return None

    sess = types.SimpleNamespace(get=lambda *a, **k: Resp())
    monkeypatch.setattr(web.requests, "Session", lambda: sess)
    out = web.read("http://a")
    assert "bad" not in out["result"]["text"]

    def timeout(*a, **k):
        raise web.requests.Timeout()

    monkeypatch.setattr(web.requests, "Session", lambda: types.SimpleNamespace(get=timeout))
    out = web.read("http://a")
    assert out["code"] == "timeout"


def test_ui_missing_cursor(monkeypatch):
    monkeypatch.setitem(sys.modules, "cursor", None)
    res = ui.what_under_mouse()
    assert res["code"] == "missing_dep"


def test_ui_ok(monkeypatch):
    monkeypatch.setitem(sys.modules, "cursor", types.SimpleNamespace(get_position=lambda: {"x": 1, "y": 2}))
    fake_win = types.SimpleNamespace(title="t")
    pgw = types.SimpleNamespace(getWindowsAt=lambda x, y: [fake_win], getActiveWindow=lambda: fake_win)
    monkeypatch.setitem(sys.modules, "pygetwindow", pgw)
    monkeypatch.setitem(sys.modules, "uia", types.SimpleNamespace(get_element_info=lambda x, y: ({}, {"role": "r", "name": "n"}, "", 0.0)))
    res = ui.what_under_mouse()
    assert res["kind"] == "ok" and res["result"]["window"]
