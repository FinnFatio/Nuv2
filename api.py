from typing import Dict
import io
import sys

# Ensure standard library modules have priority over local names like inspect.py
if "" in sys.path:
    sys.path.remove("")
    sys.path.append("")
import fastapi
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse
import resolve
import screenshot
from logger import setup, log_call

# Enable JSON logging similar to CLI tools
setup(True)

app = FastAPI()

# Caches for element details and bounds keyed by IDs
ELEMENT_CACHE: Dict[str, Dict] = {}
BOUNDS_CACHE: Dict[str, Dict] = {}


@app.get("/inspect")
@log_call
def inspect(x: int | None = Query(default=None), y: int | None = Query(default=None)):
    """Describe the element under the cursor or at provided coordinates."""
    if x is not None and y is not None:
        info = resolve.describe_under_cursor(x, y)
    else:
        info = resolve.describe_under_cursor()
    element = info.get("element", {})
    bounds = element.get("bounds")
    ELEMENT_CACHE[info["control_id"]] = element
    if bounds:
        BOUNDS_CACHE[info["control_id"]] = bounds
        BOUNDS_CACHE[info["window_id"]] = bounds
    return JSONResponse(info)


@app.get("/details")
@log_call
def details(id: str = Query(...)):
    """Return cached element details for the given control or window ID."""
    element = ELEMENT_CACHE.get(id)
    if not element:
        return JSONResponse({"error": "id not found", "code": "id_not_found"}, status_code=404)
    return JSONResponse(element)


@app.get("/snapshot")
@log_call
def snapshot(id: str | None = None, region: str | None = None):
    """Return a PNG screenshot by element ID or explicit region."""
    if (id is None) == (region is None):
        return JSONResponse(
            {"error": "provide id or region", "code": "missing_id_or_region"},
            status_code=400,
        )
    if id is not None:
        bounds = BOUNDS_CACHE.get(id)
        if not bounds:
            return JSONResponse({"error": "id not found", "code": "id_not_found"}, status_code=404)
        region_tuple = (
            bounds["left"],
            bounds["top"],
            bounds["right"],
            bounds["bottom"],
        )
    else:
        try:
            x, y, w, h = map(int, region.split(","))
        except Exception:
            return JSONResponse(
                {"error": "invalid region", "code": "invalid_region"}, status_code=400
            )
        region_tuple = (x, y, x + w, y + h)
    img = screenshot.capture(region_tuple)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
