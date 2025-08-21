from __future__ import annotations

from typing import Dict, Optional, Tuple
from primitives import Bounds, GrabResult, Point

import json
import time
import sys
import random
import threading
import atexit

import mss
from PIL import Image
import argparse
import re
from pathlib import Path
from settings import (
    CAPTURE_WIDTH,
    CAPTURE_HEIGHT,
    CAPTURE_LOG_SAMPLE_RATE,
    CAPTURE_LOG_DEST,
)
from logger import log_call, setup, COMPONENT
from cli_helpers import emit_cli_json
import metrics

ERROR_CODE_MAP = {
    "pygetwindow is required for window capture": "pygetwindow_missing",
    "No active window found": "no_active_window",
    "No window matches pattern": "window_not_found",
    "window search timeout": "window_search_timeout",
}


_SCT: "mss.mss" | None = None
_SCT_LOCK = threading.Lock()


def _log_sampled(data: Dict[str, object]) -> None:
    if CAPTURE_LOG_SAMPLE_RATE > 0 and random.random() < CAPTURE_LOG_SAMPLE_RATE:
        line = json.dumps(data)
        if CAPTURE_LOG_DEST == "stderr":
            print(line, file=sys.stderr)
        elif CAPTURE_LOG_DEST.startswith("file:"):
            path = Path(CAPTURE_LOG_DEST[5:])
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")


def _reset_sct(reason: str | None = None) -> None:
    metrics.record_fallback("resets")
    if reason is not None:
        _log_sampled({"stage": "mss.reset", "reason": reason})
    global _SCT
    with _SCT_LOCK:
        try:  # pragma: no cover - best effort cleanup
            if _SCT is not None:
                _SCT.close()
        except Exception:
            pass
        _SCT = None


def _get_sct() -> "mss.mss":
    global _SCT
    with _SCT_LOCK:
        if _SCT is None:
            _SCT = mss.mss()
        return _SCT


atexit.register(_reset_sct)


def _validate_bbox(
    left: int,
    top: int,
    right: int,
    bottom: int,
    bounds: Bounds | None = None,
) -> None:
    if right <= left or bottom <= top:
        region = (left, top, right, bottom)
        if bounds is not None:
            mon = bounds.get("monitor", "unknown")
            raise ValueError(
                f"Invalid capture region {region} within {bounds} on {mon}"
            )
        raise ValueError(f"Invalid capture region {region}")


def get_screen_bounds() -> Tuple[int, int, int, int]:
    """Return the bounding box of all monitors as (left, top, right, bottom)."""
    sct = _get_sct()
    try:
        monitor = sct.monitors[0]
    except Exception:
        _reset_sct("monitors_failed")
        sct = _get_sct()
        monitor = sct.monitors[0]
    left = monitor["left"]
    top = monitor["top"]
    right = left + monitor["width"]
    bottom = top + monitor["height"]
    return left, top, right, bottom


def get_screen_resolution() -> Tuple[int, int]:
    """Return the width and height of the virtual screen."""
    left, top, right, bottom = get_screen_bounds()
    return right - left, bottom - top


def get_monitor_bounds(label: str) -> Bounds:
    """Return bounds of monitor given its label (mon1|mon2|virtual)."""
    sct = _get_sct()
    try:
        monitors = sct.monitors
    except Exception:
        _reset_sct("monitors_failed")
        sct = _get_sct()
        monitors = sct.monitors
    if label == "virtual":
        mon = monitors[0]
    elif label.startswith("mon"):
        idx = int(label[3:])
        if idx <= 0 or idx >= len(monitors):
            raise ValueError(f"unknown monitor {label}")
        mon = monitors[idx]
    else:
        raise ValueError(f"unknown monitor {label}")
    left = mon["left"]
    top = mon["top"]
    right = left + mon["width"]
    bottom = top + mon["height"]
    return {"left": left, "top": top, "right": right, "bottom": bottom}


def health_check() -> Dict[str, object]:
    """Return basic capture bounds and latency information."""
    left, top, right, bottom = get_screen_bounds()
    sct = _get_sct()
    monitor = {"left": left, "top": top, "width": 1, "height": 1}
    start = time.perf_counter()
    try:
        sct.grab(monitor)
    except Exception:
        _reset_sct("monitors_failed")
        sct = _get_sct()
        sct.grab(monitor)
    latency_ms = int((time.perf_counter() - start) * 1000)
    return {
        "bounds": {"left": left, "top": top, "right": right, "bottom": bottom},
        "latency_ms": latency_ms,
    }


@log_call
def capture(region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
    """Capture a screenshot of the given region."""
    sct = _get_sct()
    if region is not None:
        left, top, right, bottom = region
        _validate_bbox(left, top, right, bottom)
        monitor: Dict[str, int] = {
            "left": left,
            "top": top,
            "width": right - left,
            "height": bottom - top,
        }
        bounds = get_monitor_bounds_for_point((left + right) // 2, (top + bottom) // 2)
    else:
        try:
            monitor = sct.monitors[0]  # type: ignore[index]
        except Exception:
            _reset_sct("monitors_failed")
            sct = _get_sct()
            monitor = sct.monitors[0]  # type: ignore[index]
        bounds: Bounds = {"monitor": "virtual"}
    start = time.perf_counter()
    try:
        screenshot = sct.grab(monitor)  # type: ignore[arg-type]
    except Exception:
        _reset_sct("monitors_failed")
        sct = _get_sct()
        screenshot = sct.grab(monitor)  # type: ignore[arg-type]
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    _log_sampled(
        {"time_capture_ms": elapsed_ms, "monitor": bounds.get("monitor", "unknown")}
    )
    gr: GrabResult = screenshot  # type: ignore[assignment]
    return Image.frombytes("RGB", gr.size, gr.rgb)


def get_monitor_bounds_for_point(x: int, y: int) -> Bounds:
    """Return bounds of monitor containing ``(x, y)`` or the virtual screen.

    If the point does not fall within any individual monitor, the virtual
    screen bounds are returned as a fallback.
    """
    sct = _get_sct()
    try:
        monitors = sct.monitors
    except Exception:
        _reset_sct("monitors_failed")
        sct = _get_sct()
        monitors = sct.monitors
    for idx, mon in enumerate(monitors[1:], start=1):
        left = mon["left"]
        top = mon["top"]
        right = left + mon["width"]
        bottom = top + mon["height"]
        if left <= x < right and top <= y < bottom:
            return {
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "monitor": f"mon{idx}",
            }
    mon = monitors[0]
    left = mon["left"]
    top = mon["top"]
    right = left + mon["width"]
    bottom = top + mon["height"]
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "monitor": "virtual",
    }


def capture_around(
    point: Point,
    width: int = CAPTURE_WIDTH,
    height: int = CAPTURE_HEIGHT,
    bounds: Bounds | None = None,
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """Capture a screenshot centered on the given point.

    If ``bounds`` is provided, the captured region will be clipped to lie
    within those bounds.
    """
    left = point["x"] - width // 2
    top = point["y"] - height // 2
    right = left + width
    bottom = top + height

    if bounds is None:
        bounds = get_monitor_bounds_for_point(point["x"], point["y"])

    left = max(bounds.get("left", left), left)
    top = max(bounds.get("top", top), top)
    right = min(bounds.get("right", right), right)
    bottom = min(bounds.get("bottom", bottom), bottom)

    screen_left, screen_top, screen_right, screen_bottom = get_screen_bounds()
    left = max(screen_left, left)
    top = max(screen_top, top)
    right = min(screen_right, right)
    bottom = min(screen_bottom, bottom)
    _validate_bbox(left, top, right, bottom, bounds)

    region = (left, top, right, bottom)
    return capture(region), region


def _parse_region(arg: str) -> Dict[str, int]:
    """Parse a region in the form x,y,w,h into a monitor dict."""
    x, y, w, h = map(int, arg.split(","))
    return {"left": x, "top": y, "width": w, "height": h}


def _get_windows(gw, timeout: Optional[float]) -> list:
    result = []
    exc: Exception | None = None

    def worker():
        nonlocal result, exc
        try:
            result = gw.getAllWindows()
        except Exception as e:  # pragma: no cover - defensive
            exc = e

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise SystemExit("window search timeout")
    if exc:
        raise exc
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Save a screenshot to a PNG file")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--active", action="store_true", help="capture the active window"
    )
    group.add_argument("--window", type=str, help="capture first window matching regex")
    group.add_argument("--region", type=str, help="capture explicit region x,y,w,h")
    group.add_argument("--monitor", type=str, help="capture entire monitor by label")
    parser.add_argument("--json", action="store_true", help="output JSON result")
    parser.add_argument(
        "--first", type=int, default=None, help="limit window search to first N"
    )
    parser.add_argument(
        "--timeout", type=float, default=None, help="timeout for window search"
    )
    parser.add_argument(
        "output", nargs="?", default="screenshot.png", help="output PNG path"
    )
    args = parser.parse_args()
    setup()
    COMPONENT.set("cli")
    region = None
    try:
        if args.region:
            try:
                mon = _parse_region(args.region)
            except Exception:
                raise ValueError("invalid region")
            region = (
                mon["left"],
                mon["top"],
                mon["left"] + mon["width"],
                mon["top"] + mon["height"],
            )
        elif args.monitor:
            mon = get_monitor_bounds(args.monitor)
            region = (mon["left"], mon["top"], mon["right"], mon["bottom"])
        elif args.active or args.window:
            try:
                import pygetwindow as gw
            except Exception:  # pragma: no cover - optional dependency
                raise SystemExit("pygetwindow is required for window capture")
            if args.active:
                win = gw.getActiveWindow()
                if win is None:
                    raise SystemExit("No active window found")
            else:
                pattern = re.compile(args.window, re.IGNORECASE)
                windows = _get_windows(gw, args.timeout)
                if args.first is not None:
                    windows = windows[: args.first]
                matches = [w for w in windows if pattern.search(w.title)]
                if not matches:
                    raise SystemExit("No window matches pattern")
                win = matches[0]
            region = (
                win.left,
                win.top,
                win.left + win.width,
                win.top + win.height,
            )
        img = capture(region)
    except ValueError as e:
        msg = str(e)
        code_name = "invalid_region" if msg == "invalid region" else "bad_region"
        if args.json:
            data = {"code": code_name, "message": msg}
            if code_name == "bad_region" and region is not None:
                data["region"] = region
            emit_cli_json(data, 2)
        else:
            print(msg, file=sys.stderr)
            raise SystemExit(2)
    except SystemExit as e:  # standardize CLI errors
        msg = str(e)
        code = e.code if isinstance(e.code, int) else 1
        if args.json:
            data = {"code": ERROR_CODE_MAP.get(msg, "unknown"), "message": msg}
            emit_cli_json(data, code)
        else:
            print(msg, file=sys.stderr)
            raise SystemExit(code)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    if args.json:
        result = {"output": str(out_path), "region": region}
        emit_cli_json(result, 0)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
