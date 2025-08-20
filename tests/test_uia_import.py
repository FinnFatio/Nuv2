from uia import get_element_info
import uia


def test_get_element_info_defaults_when_pywinauto_missing(monkeypatch):
    monkeypatch.setattr(uia, "UIAElementInfo", None)
    app, element, text, conf = get_element_info(10, 20)
    assert app == {"pid": None, "exe": None, "window_title": None}
    assert element == {
        "control_type": None,
        "bounds": None,
        "automation_id": None,
        "name": None,
        "is_enabled": None,
        "is_offscreen": None,
        "patterns": [],
        "affordances": {},
        "ancestors": [],
    }
    assert text == ""
    assert conf == 0.0
