from typing import Tuple, Dict, Optional
import mss
from PIL import Image
from PIL.Image import Image as PILImage  # classe para tipagem
import argparse
import re
from pathlib import Path
from settings import CAPTURE_WIDTH, CAPTURE_HEIGHT


def get_screen_bounds() -> Tuple[int, int, int, int]:
    """Return the bounding box of all monitors as (left, top, right, bottom)."""
    with mss.mss() as sct:
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


def capture(region: Tuple[int, int, int, int] = None) -> Image:
    """Capture a screenshot of the given region."""
    with mss.mss() as sct:
        if region:
            left, top, right, bottom = region
            monitor = {
                "left": left,
                "top": top,
                "width": right - left,
                "height": bottom - top,
            }
        else:
            monitor = sct.monitors[0]
        screenshot = sct.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.rgb)


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
    region = (left, top, right, bottom)
    return capture(region), region


def _parse_region(arg: str) -> Dict[str, int]:
    """Parse a region in the form x,y,w,h into a monitor dict."""
    x, y, w, h = map(int, arg.split(","))
    return {"left": x, "top": y, "width": w, "height": h}


def main() -> None:
    parser = argparse.ArgumentParser(description="Save a screenshot to a PNG file")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--active", action="store_true", help="capture the active window")
    group.add_argument("--window", type=str, help="capture first window matching regex")
    group.add_argument("--region", type=str, help="capture explicit region x,y,w,h")
    parser.add_argument("output", nargs="?", default="screenshot.png", help="output PNG path")
    args = parser.parse_args()

    monitor = None
    if args.region:
        monitor = _parse_region(args.region)
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
        monitor = {"left": win.left, "top": win.top, "width": win.width, "height": win.height}

    with mss.mss() as sct:
        if monitor is None:
            monitor = sct.monitors[0]
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
