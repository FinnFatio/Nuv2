import resolve


def test_uia_metadata_propagates(monkeypatch):
    window = {
        "handle": 1,
        "active": True,
        "pid": 42,
        "title": "Win",
        "app_path": "path",
        "bounds": {"left": 0, "top": 0, "right": 10, "bottom": 10},
    }
    element = {
        "control_type": "Text",
        "name": "name",
        "value": "",
        "is_enabled": True,
        "is_offscreen": False,
        "bounds": {"left": 1, "top": 1, "right": 5, "bottom": 5},
        "patterns": [],
        "affordances": {},
        "ancestors": [],
    }
    monkeypatch.setattr(
        resolve,
        "get_element_info",
        lambda x, y: (window, element, "", 0.0),
    )
    monkeypatch.setattr(
        resolve, "capture_around", lambda pos, bounds=None: ("img", (0, 0, 0, 0))
    )
    monkeypatch.setattr(resolve, "extract_text", lambda img, region=None: ("", 0.0))
    info = resolve.describe_under_cursor(0, 0)
    assert "value" in info["element"]
    assert "handle" in info["window"]
    assert "active" in info["window"]
    b = info["element"]["bounds"]
    assert b["left"] < b["right"]
    assert b["top"] < b["bottom"]
