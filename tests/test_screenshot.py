import os
import sys
import types

# Stub out mss before importing screenshot
sys.modules["mss"] = types.SimpleNamespace()

# Stub out PIL before importing screenshot
pil_module = types.ModuleType("PIL")
pil_module.Image = object
sys.modules["PIL"] = pil_module

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import screenshot


def stub_capture(region):
    return region


def test_capture_around_near_top_left(monkeypatch):
    monkeypatch.setattr(screenshot, "get_screen_resolution", lambda: (800, 600))
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": 10, "y": 10}
    img, region = screenshot.capture_around(point, width=100, height=100)
    assert region == (0, 0, 60, 60)
    assert img == region


def test_capture_around_near_bottom_right(monkeypatch):
    monkeypatch.setattr(screenshot, "get_screen_resolution", lambda: (800, 600))
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": 790, "y": 590}
    img, region = screenshot.capture_around(point, width=100, height=100)
    assert region == (740, 540, 800, 600)
    assert img == region
