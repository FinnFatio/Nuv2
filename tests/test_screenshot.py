import os
import sys
import types
import io
import json

import pytest

# Stub out mss before importing screenshot
sys.modules["mss"] = types.SimpleNamespace()

# Stub out PIL before importing screenshot
pil_module = types.ModuleType("PIL")
image_module = types.ModuleType("PIL.Image")
image_module.Image = object
pil_module.Image = image_module
sys.modules["PIL"] = pil_module
sys.modules["PIL.Image"] = image_module

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import screenshot


def stub_capture(region):
    return region


def test_capture_around_near_top_left(monkeypatch):
    monkeypatch.setattr(screenshot, "get_screen_bounds", lambda: (0, 0, 800, 600))
    monkeypatch.setattr(
        screenshot,
        "get_monitor_bounds_for_point",
        lambda x, y: {"left": 0, "top": 0, "right": 800, "bottom": 600},
    )
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": 10, "y": 10}
    img, region = screenshot.capture_around(point, width=100, height=100)
    assert region == (0, 0, 60, 60)
    assert img == region


def test_capture_around_near_bottom_right(monkeypatch):
    monkeypatch.setattr(screenshot, "get_screen_bounds", lambda: (0, 0, 800, 600))
    monkeypatch.setattr(
        screenshot,
        "get_monitor_bounds_for_point",
        lambda x, y: {"left": 0, "top": 0, "right": 800, "bottom": 600},
    )
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": 790, "y": 590}
    img, region = screenshot.capture_around(point, width=100, height=100)
    assert region == (740, 540, 800, 600)
    assert img == region


def test_capture_around_within_bounds(monkeypatch):
    monkeypatch.setattr(screenshot, "get_screen_bounds", lambda: (0, 0, 800, 600))
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": 400, "y": 300}
    bounds = {"left": 380, "top": 290, "right": 420, "bottom": 310}
    img, region = screenshot.capture_around(point, width=100, height=100, bounds=bounds)
    assert region == (380, 290, 420, 310)
    assert img == region


def test_capture_around_multi_monitor(monkeypatch):
    # Simulate two monitors side by side with the primary at (0,0)
    monkeypatch.setattr(screenshot, "get_screen_bounds", lambda: (-800, 0, 800, 600))
    def fake_get_monitor_bounds(x, y):
        if x < 0:
            return {"left": -800, "top": 0, "right": 0, "bottom": 600}
        return {"left": 0, "top": 0, "right": 800, "bottom": 600}

    monkeypatch.setattr(screenshot, "get_monitor_bounds_for_point", fake_get_monitor_bounds)
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": -790, "y": 10}
    img, region = screenshot.capture_around(point, width=100, height=100)
    assert region == (-800, 0, -740, 60)
    assert img == region


def test_get_monitor_bounds_for_point(monkeypatch):
    monitors = [
        {"left": 0, "top": 0, "width": 1600, "height": 600},
        {"left": 0, "top": 0, "width": 800, "height": 600},
        {"left": 800, "top": 0, "width": 800, "height": 600},
    ]

    class DummySCT:
        def __init__(self, mons):
            self.monitors = mons

        def close(self):
            pass

    dummy = DummySCT(monitors)
    monkeypatch.setattr(screenshot, "_SCT", dummy)
    assert screenshot.get_monitor_bounds_for_point(10, 10) == {
        "left": 0,
        "top": 0,
        "right": 800,
        "bottom": 600,
        "monitor": "mon1",
    }
    assert screenshot.get_monitor_bounds_for_point(810, 10) == {
        "left": 800,
        "top": 0,
        "right": 1600,
        "bottom": 600,
        "monitor": "mon2",
    }
    # Outside any monitor falls back to virtual screen
    assert screenshot.get_monitor_bounds_for_point(1700, 10) == {
        "left": 0,
        "top": 0,
        "right": 1600,
        "bottom": 600,
        "monitor": "virtual",
    }


def test_capture_logs_time_ms(monkeypatch):
    class DummyGrab:
        size = (1, 1)
        rgb = b"\x00\x00\x00"

    class DummySCT:
        def grab(self, monitor):
            return DummyGrab()

    monkeypatch.setattr(screenshot, "_get_sct", lambda: DummySCT())
    monkeypatch.setattr(
        screenshot, "Image", types.SimpleNamespace(frombytes=lambda *a, **k: object())
    )
    monkeypatch.setattr(screenshot, "CAPTURE_LOG_SAMPLE_RATE", 1.0)
    monkeypatch.setattr(screenshot.random, "random", lambda: 0.0)

    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)

    screenshot.capture((0, 0, 1, 1))

    data = json.loads(buf.getvalue().strip())
    assert "time_capture_ms" in data


def test_capture_invalid_region(monkeypatch):
    monkeypatch.setattr(screenshot, "_get_sct", lambda: object())
    with pytest.raises(ValueError):
        screenshot.capture((0, 0, 0, 10))


def test_capture_around_zero_area(monkeypatch):
    monkeypatch.setattr(screenshot, "get_screen_bounds", lambda: (0, 0, 800, 600))
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": 10, "y": 10}
    bounds = {"left": 10, "top": 10, "right": 10, "bottom": 20}
    with pytest.raises(ValueError):
        screenshot.capture_around(point, width=100, height=100, bounds=bounds)


def test_capture_log_creates_directory(monkeypatch, tmp_path):
    class DummyGrab:
        size = (1, 1)
        rgb = b"\x00\x00\x00"

    class DummySCT:
        def grab(self, monitor):
            return DummyGrab()

    monkeypatch.setattr(screenshot, "_get_sct", lambda: DummySCT())
    monkeypatch.setattr(
        screenshot, "Image", types.SimpleNamespace(frombytes=lambda *a, **k: object())
    )
    monkeypatch.setattr(screenshot, "CAPTURE_LOG_SAMPLE_RATE", 1.0)
    monkeypatch.setattr(screenshot.random, "random", lambda: 0.0)
    path = tmp_path / "logs" / "cap.log"
    monkeypatch.setattr(screenshot, "CAPTURE_LOG_DEST", f"file:{path}")

    screenshot.capture((0, 0, 1, 1))

    assert path.exists()
    data = json.loads(path.read_text().strip())
    assert "time_capture_ms" in data


def test_main_errors_return_json(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["screenshot.py", "--region", "bad", "out.png"])
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 2
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert "error" in data
