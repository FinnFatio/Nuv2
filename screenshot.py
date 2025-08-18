from typing import Tuple, Dict, Optional
import mss
from PIL import Image


def get_screen_resolution() -> Tuple[int, int]:
    """Return the current screen resolution."""
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        return monitor["width"], monitor["height"]


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
    width: int = 300,
    height: int = 120,
    bounds: Optional[Dict[str, int]] = None,
) -> Tuple[Image, Tuple[int, int, int, int]]:
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

    screen_width, screen_height = get_screen_resolution()
    left = max(0, left)
    top = max(0, top)
    right = min(screen_width, right)
    bottom = min(screen_height, bottom)
    region = (left, top, right, bottom)
    return capture(region), region
