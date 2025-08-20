from __future__ import annotations

from typing import Tuple, Dict, Optional

import json
import time
import sys
import random
import threading
import atexit

import mss
from PIL import Image
from PIL.Image import Image as PILImage  # classe para tipagem
import argparse
import re
from pathlib import Path
from settings import (
    CAPTURE_WIDTH,
    CAPTURE_HEIGHT,
    CAPTURE_LOG_SAMPLE_RATE,
    CAPTURE_LOG_DEST,
)


_SCT: "mss.mss" | None = None
_SCT_LOCK = threading.Lock()


def _reset_sct() -> None:
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
    bounds: Optional[Dict[str, int]] = None,
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
        _reset_sct()
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


def capture(region: Tuple[int, int, int, int] = None) -> PILImage:
    """Capture a screenshot of the given region."""
    sct = _get_sct()
    if region:
        left, top, right, bottom = region
        _validate_bbox(left, top, right, bottom)
        monitor = {
            "left": left,
            "top": top,
            "width": right - left,
            "height": bottom - top,
        }
        bounds = get_monitor_bounds_for_point((left + right) // 2, (top + bottom) // 2)
    else:
        try:
            monitor = sct.monitors[0]
        except Exception:
            _reset_sct()
            sct = _get_sct()
            monitor = sct.monitors[0]
        bounds = {"monitor": "virtual"}
    start = time.perf_counter()
    try:
        screenshot = sct.grab(monitor)
    except Exception:
        _reset_sct()
        sct = _get_sct()
        screenshot = sct.grab(monitor)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    if CAPTURE_LOG_SAMPLE_RATE > 0 and random.random() < CAPTURE_LOG_SAMPLE_RATE:
        log_line = json.dumps(
            {"time_capture_ms": elapsed_ms, "monitor": bounds.get("monitor", "unknown")}
        )
        if CAPTURE_LOG_DEST == "stderr":
            print(log_line, file=sys.stderr)
        elif CAPTURE_LOG_DEST.startswith("file:"):
            path = Path(CAPTURE_LOG_DEST[5:])
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(log_line + "\n")
    return Image.frombytes("RGB", screenshot.size, screenshot.rgb)


def get_monitor_bounds_for_point(x: int, y: int) -> Dict[str, int]:
    """Return bounds of monitor containing ``(x, y)`` or the virtual screen.

    If the point does not fall within any individual monitor, the virtual
    screen bounds are returned as a fallback.
    """
    sct = _get_sct()
    try:
        monitors = sct.monitors
    except Exception:
        _reset_sct()
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
    point: Dict[str, int],
    width: int = CAPTURE_WIDTH,
    height: int = CAPTURE_HEIGHT,
    bounds: Optional[Dict[str, int]] = None,
) -> Tuple[PILImage, Tuple[int, int, int, int]]:
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

    if bounds:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Save a screenshot to a PNG file")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--active", action="store_true", help="capture the active window"
    )
    group.add_argument("--window", type=str, help="capture first window matching regex")
    group.add_argument("--region", type=str, help="capture explicit region x,y,w,h")
    parser.add_argument("--json", action="store_true", help="output JSON result")
    parser.add_argument(
        "output", nargs="?", default="screenshot.png", help="output PNG path"
    )
    args = parser.parse_args()
    region = None
    try:
        if args.region:
            mon = _parse_region(args.region)
            region = (
                mon["left"],
                mon["top"],
                mon["left"] + mon["width"],
                mon["top"] + mon["height"],
            )
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
                pattern = re.compile(args.window)
                matches = [w for w in gw.getAllWindows() if pattern.search(w.title)]
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
        data = {"error": str(e)}
        if region is not None:
            data["region"] = region
        print(json.dumps(data))
        sys.exit(2)
    except SystemExit as e:  # standardize CLI errors as JSON
        data = {"error": str(e)}
        print(json.dumps(data))
        code = e.code if isinstance(e.code, int) else 1
        sys.exit(code)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    if args.json:
        result = {"output": str(out_path), "region": region}
        print(json.dumps(result))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
