import sys
import types
import hashlib

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


def get_resolve():
    import resolve as _r

    return _r


def test_describe_prefers_uia_when_visible(monkeypatch):
    resolve = get_resolve()
    window = {}
    element = {
        "bounds": {"left": 0, "top": 0, "right": 100, "bottom": 100},
        "is_offscreen": False,
        "is_enabled": True,
        "control_type": "Edit",
        "name": "foo",
        "value": "uia_text",
    }
    monkeypatch.setattr(
        resolve, "get_element_info", lambda x, y: (window, element, "uia_text", 0.9)
    )
    monkeypatch.setattr(
        resolve, "capture_around", lambda pos, bounds=None: ("img", (0, 0, 0, 0))
    )
    monkeypatch.setattr(resolve, "extract_text", lambda img: ("ocr_text", 0.5))
    result = resolve.describe_under_cursor(10, 10)
    assert result["text"]["chosen"] == "uia_text"
    assert result["source"] == "uia"
    # timings and errors
    for step in ["get_element_info", "capture_around", "extract_text"]:
        assert step in result["timings"]
        t = result["timings"][step]
        assert t["start"] <= t["end"]
    assert "get_position" not in result["timings"]
    assert result["errors"] == {}


def test_describe_prefers_ocr_when_offscreen(monkeypatch):
    resolve = get_resolve()
    window = {}
    element = {
        "bounds": {"left": 0, "top": 0, "right": 100, "bottom": 100},
        "is_offscreen": True,
        "is_enabled": True,
        "control_type": "Edit",
        "name": "fo",
        "value": "",
    }
    monkeypatch.setattr(
        resolve, "get_element_info", lambda x, y: (window, element, "uia_text", 0.9)
    )
    monkeypatch.setattr(
        resolve, "capture_around", lambda pos, bounds=None: ("img", (0, 0, 0, 0))
    )
    monkeypatch.setattr(resolve, "extract_text", lambda img: ("ocr_text", 0.5))
    result = resolve.describe_under_cursor(10, 10)
    assert result["text"]["chosen"] == "ocr_text"
    assert result["source"] == "ocr"


def test_ids_and_cache(monkeypatch):
    resolve = get_resolve()
    monkeypatch.setattr(resolve, "RUNTIME_SALT", "salt")
    ancestors = [
        {"control_type": "Window", "name": "Main"},
        {"control_type": "Pane", "name": "Content"},
        {"control_type": "Edit", "name": "Input"},
    ]
    window = {
        "pid": 123,
        "title": "Main",
        "app_path": "app.exe",
        "handle": 1,
        "active": True,
        "bounds": None,
    }
    element = {
        "bounds": {"left": 0, "top": 0, "right": 100, "bottom": 100},
        "is_offscreen": False,
        "affordances": {"editable": True},
        "ancestors": ancestors,
    }
    monkeypatch.setattr(
        resolve, "get_element_info", lambda x, y: (window, element, "uia", 0.9)
    )
    monkeypatch.setattr(
        resolve, "capture_around", lambda pos, bounds=None: ("img", (0, 0, 0, 0))
    )
    monkeypatch.setattr(resolve, "extract_text", lambda img: ("ocr", 0.5))
    result = resolve.describe_under_cursor(0, 0)
    window_path = "/Window:Main"
    control_path = "/Window:Main/Pane:Content/Edit:Input"
    expected_window_id = hashlib.sha256(f"123|{window_path}|salt".encode()).hexdigest()[
        :16
    ]
    expected_control_id = hashlib.sha256(
        f"123|{control_path}|salt".encode()
    ).hexdigest()[:16]
    assert result["window_id"] == expected_window_id
    assert result["control_id"] == expected_control_id
    assert resolve.ID_CACHE["last_window_id"] == expected_window_id
    assert resolve.ID_CACHE["last_editable_control_id"] == expected_control_id


def test_error_capture(monkeypatch):
    resolve = get_resolve()
    window = {}
    element = {
        "bounds": {"left": 0, "top": 0, "right": 100, "bottom": 100},
        "is_offscreen": False,
    }
    monkeypatch.setattr(
        resolve, "get_element_info", lambda x, y: (window, element, "uia_text", 0.9)
    )
    monkeypatch.setattr(
        resolve, "capture_around", lambda pos, bounds=None: ("img", (0, 0, 0, 0))
    )

    def boom(img):
        raise ValueError("fail")

    monkeypatch.setattr(resolve, "extract_text", boom)
    result = resolve.describe_under_cursor(10, 10)
    assert "extract_text" in result["errors"]


def test_describe_uses_get_position_when_coords_missing(monkeypatch):
    resolve = get_resolve()
    called = {"count": 0}

    def fake_get_position():
        called["count"] += 1
        return {"x": 5, "y": 6}

    window = {}
    element = {
        "bounds": {"left": 0, "top": 0, "right": 10, "bottom": 10},
        "is_offscreen": False,
    }
    monkeypatch.setattr(resolve, "get_position", fake_get_position)
    monkeypatch.setattr(
        resolve, "get_element_info", lambda x, y: (window, element, "uia", 0.9)
    )
    monkeypatch.setattr(
        resolve, "capture_around", lambda pos, bounds=None: ("img", (0, 0, 0, 0))
    )
    monkeypatch.setattr(resolve, "extract_text", lambda img: ("ocr", 0.5))
    result = resolve.describe_under_cursor()
    assert called["count"] == 1
    assert result["cursor"] == {"x": 5, "y": 6}
    assert "get_position" in result["timings"]
