from uia import get_element_info
import uia


def test_get_element_info_defaults_when_pywinauto_missing(monkeypatch):
    monkeypatch.setattr(uia, "PUIAElementInfo", None)
    window, element, text, conf = get_element_info(10, 20)
    assert window == {
        "handle": None,
        "active": None,
        "pid": None,
        "title": None,
        "app_path": None,
        "bounds": None,
    }
    assert element == {
        "control_type": None,
        "automation_id": None,
        "name": None,
        "value": None,
        "role": None,
        "is_enabled": None,
        "is_offscreen": None,
        "bounds": None,
        "patterns": [],
        "affordances": {},
        "ancestors": [],
    }
    assert text == ""
    assert conf == 0.0
