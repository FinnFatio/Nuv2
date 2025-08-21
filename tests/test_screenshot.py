import sys
import types
import io
import json

import pytest
import metrics

# Stub out mss before importing screenshot
sys.modules["mss"] = types.SimpleNamespace()

# Stub out PIL before importing screenshot
pil_module = types.ModuleType("PIL")
image_module = types.ModuleType("PIL.Image")
image_module.Image = object
pil_module.Image = image_module
sys.modules["PIL"] = pil_module
sys.modules["PIL.Image"] = image_module


def get_screenshot():
    import screenshot as _s

    return _s


def stub_capture(region):
    return region


def test_capture_around_near_top_left(monkeypatch):
    screenshot = get_screenshot()
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
    screenshot = get_screenshot()
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
    screenshot = get_screenshot()
    monkeypatch.setattr(screenshot, "get_screen_bounds", lambda: (0, 0, 800, 600))
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": 400, "y": 300}
    bounds = {"left": 380, "top": 290, "right": 420, "bottom": 310}
    img, region = screenshot.capture_around(point, width=100, height=100, bounds=bounds)
    assert region == (380, 290, 420, 310)
    assert img == region


def test_capture_around_multi_monitor(monkeypatch):
    screenshot = get_screenshot()
    # Simulate two monitors side by side with the primary at (0,0)
    monkeypatch.setattr(screenshot, "get_screen_bounds", lambda: (-800, 0, 800, 600))

    def fake_get_monitor_bounds(x, y):
        if x < 0:
            return {"left": -800, "top": 0, "right": 0, "bottom": 600}
        return {"left": 0, "top": 0, "right": 800, "bottom": 600}

    monkeypatch.setattr(
        screenshot, "get_monitor_bounds_for_point", fake_get_monitor_bounds
    )
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": -790, "y": 10}
    img, region = screenshot.capture_around(point, width=100, height=100)
    assert region == (-800, 0, -740, 60)
    assert img == region


def test_get_monitor_bounds_for_point(monkeypatch):
    screenshot = get_screenshot()
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
    screenshot = get_screenshot()

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
    monkeypatch.setattr(
        screenshot, "get_monitor_bounds_for_point", lambda *a, **k: {"monitor": "mon1"}
    )

    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)

    screenshot.capture((0, 0, 1, 1))

    data = json.loads(buf.getvalue().strip())
    assert "time_capture_ms" in data
    assert "monitor" in data


def test_capture_invalid_region(monkeypatch):
    screenshot = get_screenshot()
    monkeypatch.setattr(screenshot, "_get_sct", lambda: object())
    with pytest.raises(ValueError):
        screenshot.capture((0, 0, 0, 10))


def test_capture_around_zero_area(monkeypatch):
    screenshot = get_screenshot()
    monkeypatch.setattr(screenshot, "get_screen_bounds", lambda: (0, 0, 800, 600))
    monkeypatch.setattr(screenshot, "capture", stub_capture)
    point = {"x": 10, "y": 10}
    bounds = {"left": 10, "top": 10, "right": 10, "bottom": 20}
    with pytest.raises(ValueError):
        screenshot.capture_around(point, width=100, height=100, bounds=bounds)


def test_capture_log_creates_directory(monkeypatch, tmp_path):
    screenshot = get_screenshot()

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
    monkeypatch.setattr(
        screenshot, "get_monitor_bounds_for_point", lambda *a, **k: {"monitor": "mon1"}
    )

    screenshot.capture((0, 0, 1, 1))

    assert path.exists()
    data = json.loads(path.read_text().strip())
    assert "time_capture_ms" in data
    assert "monitor" in data


def test_get_screen_bounds_recovers_from_failure(monkeypatch):
    screenshot = get_screenshot()

    class BadSCT:
        def close(self):
            pass

        @property
        def monitors(self):
            raise RuntimeError("boom")

    class GoodSCT:
        monitors = [{"left": 0, "top": 0, "width": 100, "height": 100}]

    scts = iter([BadSCT(), GoodSCT()])
    calls = []

    def fake_get_sct():
        calls.append(None)
        return next(scts)

    reset_called = []

    def fake_reset(reason=None):
        reset_called.append(reason)

    monkeypatch.setattr(screenshot, "_get_sct", fake_get_sct)
    monkeypatch.setattr(screenshot, "_reset_sct", fake_reset)

    bounds = screenshot.get_screen_bounds()
    assert bounds == (0, 0, 100, 100)
    assert len(calls) == 2
    assert reset_called


def test_reset_sct_logs_reason(monkeypatch):
    screenshot = get_screenshot()
    screenshot._SCT = types.SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(screenshot, "CAPTURE_LOG_SAMPLE_RATE", 1.0)
    monkeypatch.setattr(screenshot.random, "random", lambda: 0.0)
    monkeypatch.setattr(screenshot, "CAPTURE_LOG_DEST", "stderr")
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    screenshot._reset_sct("monitors_failed")
    data = json.loads(buf.getvalue().strip())
    assert data["stage"] == "mss.reset"
    assert data["reason"] == "monitors_failed"


def test_reset_records_metric(monkeypatch):
    screenshot = get_screenshot()
    metrics.reset()
    screenshot._SCT = types.SimpleNamespace(close=lambda: None)
    screenshot._reset_sct("forced")
    summary = metrics.summary()
    assert summary["resets_total"] == 1
    assert summary["fallbacks"]["resets"] == 1


def test_health_check(monkeypatch):
    screenshot = get_screenshot()

    class DummySCT:
        monitors = [{"left": 0, "top": 0, "width": 1, "height": 1}]

        def grab(self, monitor):
            return types.SimpleNamespace()

    monkeypatch.setattr(screenshot, "_get_sct", lambda: DummySCT())
    data = screenshot.health_check()
    assert set(data.keys()) == {"bounds", "latency_ms"}
    bounds = data["bounds"]
    assert {"left", "top", "right", "bottom"} <= bounds.keys()
    assert isinstance(data["latency_ms"], int)
    assert data["latency_ms"] >= 0


def test_main_negative_region_exit_code(monkeypatch, capsys):
    screenshot = get_screenshot()

    def bad_capture(region):
        raise ValueError("Invalid capture region")

    monkeypatch.setattr(screenshot, "capture", bad_capture)
    monkeypatch.setattr(
        sys,
        "argv",
        ["screenshot.py", "--json", "--region", "0,0,-1,1", "out.png"],
    )
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 2
    data = json.loads(capsys.readouterr().out.strip())
    assert data["error"]["code"] == "bad_region"


def test_main_errors_return_json(monkeypatch, capsys):
    screenshot = get_screenshot()
    monkeypatch.setattr(
        sys, "argv", ["screenshot.py", "--json", "--region", "bad", "out.png"]
    )
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 2
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data["error"]["code"] == "invalid_region"


def test_main_requires_pygetwindow_outputs_json(monkeypatch, capsys):
    screenshot = get_screenshot()
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pygetwindow":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(sys, "argv", ["screenshot.py", "--json", "--active"])
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data["error"]["code"] == "pygetwindow_missing"


def test_main_json_success(monkeypatch, tmp_path, capsys):
    screenshot = get_screenshot()

    class DummyImg:
        def save(self, path):
            pass

    monkeypatch.setattr(screenshot, "capture", lambda region: DummyImg())
    out_file = tmp_path / "out.png"
    monkeypatch.setattr(
        sys,
        "argv",
        ["screenshot.py", "--json", "--region", "0,0,1,1", str(out_file)],
    )
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 0
    out = json.loads(capsys.readouterr().out.strip())
    assert out["data"]["output"] == str(out_file)
    assert out["data"]["region"] == [0, 0, 1, 1]


def test_main_window_not_found_outputs_json(monkeypatch, capsys):
    screenshot = get_screenshot()

    class DummyWin:
        title = "Other"

    gw_module = types.SimpleNamespace(getAllWindows=lambda: [DummyWin()])
    monkeypatch.setitem(sys.modules, "pygetwindow", gw_module)
    monkeypatch.setattr(sys, "argv", ["screenshot.py", "--json", "--window", "Missing"])
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 1
    data = json.loads(capsys.readouterr().out.strip())
    assert data["error"]["code"] == "window_not_found"


def test_main_window_ignore_case(monkeypatch, tmp_path):
    screenshot = get_screenshot()

    class DummyImg:
        def save(self, path):
            pass

    class DummyWin:
        title = "NotePad"
        left = top = 0
        width = height = 1

    gw_module = types.SimpleNamespace(getAllWindows=lambda: [DummyWin()])
    monkeypatch.setitem(sys.modules, "pygetwindow", gw_module)
    out_file = tmp_path / "out.png"
    monkeypatch.setattr(
        sys, "argv", ["screenshot.py", "--window", "notepad", str(out_file)]
    )
    monkeypatch.setattr(screenshot, "capture", lambda region: DummyImg())
    screenshot.main()


def test_main_window_first_limit(monkeypatch, capsys):
    screenshot = get_screenshot()

    class WinA:
        title = "Other"
        left = top = 0
        width = height = 1

    class WinB:
        title = "Target"
        left = top = 0
        width = height = 1

    gw_module = types.SimpleNamespace(getAllWindows=lambda: [WinA(), WinB()])
    monkeypatch.setitem(sys.modules, "pygetwindow", gw_module)
    monkeypatch.setattr(
        sys, "argv", ["screenshot.py", "--json", "--window", "Target", "--first", "1"]
    )
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 1
    data = json.loads(capsys.readouterr().out.strip())
    assert data["error"]["code"] == "window_not_found"


def test_main_json_includes_null_region(monkeypatch, tmp_path, capsys):
    screenshot = get_screenshot()

    class DummyImg:
        def save(self, path):
            pass

    monkeypatch.setattr(screenshot, "capture", lambda region: DummyImg())
    out_file = tmp_path / "out.png"
    monkeypatch.setattr(sys, "argv", ["screenshot.py", "--json", str(out_file)])
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 0
    data = json.loads(capsys.readouterr().out.strip())
    assert data["data"]["output"] == str(out_file)
    assert data["data"]["region"] is None


def test_main_monitor_capture(monkeypatch, tmp_path):
    screenshot = get_screenshot()

    class DummyImg:
        def save(self, path):
            pass

    def fake_capture(region):
        assert region == (2, 0, 4, 2)
        return DummyImg()

    class DummySCT:
        monitors = [
            {"left": 0, "top": 0, "width": 4, "height": 2},
            {"left": 0, "top": 0, "width": 2, "height": 2},
            {"left": 2, "top": 0, "width": 2, "height": 2},
        ]

    monkeypatch.setattr(screenshot, "_get_sct", lambda: DummySCT())
    monkeypatch.setattr(screenshot, "capture", fake_capture)
    out_file = tmp_path / "out.png"
    monkeypatch.setattr(
        sys, "argv", ["screenshot.py", "--monitor", "mon2", str(out_file)]
    )
    screenshot.main()


def test_main_window_timeout(monkeypatch, capsys):
    screenshot = get_screenshot()
    import time

    def slow_windows():
        time.sleep(1)
        return []

    gw_module = types.SimpleNamespace(getAllWindows=slow_windows)
    monkeypatch.setitem(sys.modules, "pygetwindow", gw_module)
    monkeypatch.setattr(
        sys, "argv", ["screenshot.py", "--json", "--window", "a", "--timeout", "0.01"]
    )
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 1
    data = json.loads(capsys.readouterr().out.strip())
    assert data["error"]["code"] == "window_search_timeout"


def test_cli_success_json_no_region(monkeypatch, capsys, tmp_path):
    screenshot = get_screenshot()

    class DummyImg:
        def save(self, path):
            pass

    monkeypatch.setattr(screenshot, "capture", lambda region: DummyImg())
    out_file = tmp_path / "out.png"
    monkeypatch.setattr(sys, "argv", ["screenshot.py", "--json", str(out_file)])
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 0
    data = json.loads(capsys.readouterr().out.strip())
    assert data["data"]["region"] is None


def test_cli_window_no_match(monkeypatch, capsys, tmp_path):
    screenshot = get_screenshot()
    dummy_gw = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "pygetwindow", dummy_gw)
    monkeypatch.setattr(screenshot, "_get_windows", lambda gw, t: [])
    out_file = tmp_path / "out.png"
    monkeypatch.setattr(
        sys, "argv", ["screenshot.py", "--json", "--window", "nope", str(out_file)]
    )
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 1
    data = json.loads(capsys.readouterr().out.strip())
    assert data["error"]["code"] == "window_not_found"


def test_cli_invalid_region(monkeypatch, capsys, tmp_path):
    screenshot = get_screenshot()

    class DummyImg:
        def save(self, path):
            pass

    def fake_capture(region):
        screenshot._validate_bbox(*region)
        return DummyImg()

    monkeypatch.setattr(screenshot, "capture", fake_capture)
    out_file = tmp_path / "out.png"
    monkeypatch.setattr(
        sys, "argv", ["screenshot.py", "--json", "--region", "0,0,-1,-1", str(out_file)]
    )
    with pytest.raises(SystemExit) as exc:
        screenshot.main()
    assert exc.value.code == 2
    data = json.loads(capsys.readouterr().out.strip())
    assert data["error"]["code"] == "bad_region"
