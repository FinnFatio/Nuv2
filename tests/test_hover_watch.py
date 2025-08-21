import sys
import time
import hover_watch


def test_hover_watch_uses_settings(monkeypatch):
    monkeypatch.setattr(hover_watch, "HOVER_WATCH_HZ", 2.0)
    monkeypatch.setattr(hover_watch, "HOVER_WATCH_RUN_AS_ADMIN", False)
    monkeypatch.setattr(sys, "argv", ["hover_watch.py"])
    called = {}

    def fake_desc():
        return {}

    def fake_emit(info):
        called["emitted"] = True

    def fake_sleep(delay):
        called["delay"] = delay
        raise KeyboardInterrupt

    monkeypatch.setattr(hover_watch, "describe_under_cursor", fake_desc)
    monkeypatch.setattr(hover_watch, "emit_cli_json_line", fake_emit)
    monkeypatch.setattr(time, "sleep", fake_sleep)
    hover_watch.main()
    assert called["emitted"]
    assert called["delay"] == 0.5
