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
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": 400, "y": 300}
    bounds = {"left": 380, "top": 290, "right": 420, "bottom": 310}
    img, region = screenshot.capture_around(point, width=100, height=100, bounds=bounds)
    assert region == (380, 290, 420, 310)
    assert img == region


def test_capture_around_multi_monitor(monkeypatch):
    # Simulate two monitors side by side with the primary at (0,0)
    def bounds_for_point(x, y):
        if x < 0:
            return {"left": -800, "top": 0, "right": 0, "bottom": 600}
        return {"left": 0, "top": 0, "right": 800, "bottom": 600}

    monkeypatch.setattr(screenshot, "get_monitor_bounds_for_point", bounds_for_point)
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": -790, "y": 10}
    img, region = screenshot.capture_around(point, width=100, height=100)
    assert region == (-800, 0, -740, 60)
    assert img == region


def test_capture_around_multi_monitor_mismatched_heights(monkeypatch):
    # Left monitor is shorter (500px height) than right monitor (600px)
    def bounds_for_point(x, y):
        if x < 0:
            return {"left": -800, "top": 0, "right": 0, "bottom": 500}
        return {"left": 0, "top": 0, "right": 800, "bottom": 600}

    monkeypatch.setattr(screenshot, "get_monitor_bounds_for_point", bounds_for_point)
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": -10, "y": 490}
    img, region = screenshot.capture_around(point, width=100, height=100)
    assert region == (-60, 440, 0, 500)
    assert img == region


def test_get_monitor_bounds_for_point(monkeypatch):
    class DummySCT:
        monitors = [
            {"left": -800, "top": 0, "width": 1600, "height": 600},
            {"left": -800, "top": 0, "width": 800, "height": 600},
            {"left": 0, "top": 0, "width": 800, "height": 600},
        ]

    monkeypatch.setattr(screenshot, "_get_sct", lambda: DummySCT)

    bounds = screenshot.get_monitor_bounds_for_point(-10, 10)
    assert bounds == {"left": -800, "top": 0, "right": 0, "bottom": 600}

    bounds = screenshot.get_monitor_bounds_for_point(1000, 10)
    assert bounds == {"left": -800, "top": 0, "right": 800, "bottom": 600}
