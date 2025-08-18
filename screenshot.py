from typing import Tuple, Dict
import mss
from PIL import Image


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


def capture_around(point: Dict[str, int], width: int = 300, height: int = 120) -> Tuple[Image, Tuple[int, int, int, int]]:
    """Capture a screenshot centered on the given point."""
    left = point["x"] - width // 2
    top = point["y"] - height // 2
    right = left + width
    bottom = top + height
    region = (left, top, right, bottom)
    return capture(region), region
