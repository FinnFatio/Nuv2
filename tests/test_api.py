import os
import sys
import types

pytesseract_module = types.ModuleType("pytesseract")
pytesseract_module.image_to_string = lambda *a, **k: ""
sys.modules["pytesseract"] = pytesseract_module

for k in list(sys.modules):
    if k.startswith("PIL"):
        sys.modules.pop(k)

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
import api


def fake_describe_under_cursor(x=None, y=None):
    return {
        "cursor": {"x": 1, "y": 2},
        "app": {},
        "element": {
            "bounds": {"left": 0, "top": 0, "right": 1, "bottom": 1},
            "patterns": ["ValuePattern"],
            "affordances": {},
            "ancestors": [],
        },
        "text": {"uia": "", "ocr": "", "chosen": ""},
        "confidence": {"uia": 0.0, "ocr": 0.0},
        "source": "ocr",
        "window_id": "w1",
        "control_id": "c1",
        "timings": {},
        "errors": {},
    }


class FakeImage:
    def save(self, buf, format):
        buf.write(b"fake")


def fake_capture(region):
    return FakeImage()


def test_api_routes(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    monkeypatch.setattr(api.resolve, "describe_under_cursor", fake_describe_under_cursor)
    monkeypatch.setattr(api.screenshot, "capture", fake_capture)
    client = TestClient(api.app)

    resp = client.get("/inspect")
    assert resp.status_code == 200
    data = resp.json()
    assert data["control_id"] == "c1"

    resp = client.get("/details", params={"id": "c1"})
    assert resp.status_code == 200
    assert resp.json()["patterns"] == ["ValuePattern"]

    resp = client.get("/snapshot", params={"region": "0,0,1,1"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"

    resp = client.get("/snapshot", params={"id": "c1"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def test_inspect_with_coordinates(monkeypatch):
    recorded = {}

    def fake_desc(x=None, y=None):
        recorded["coords"] = (x, y)
        return fake_describe_under_cursor(x, y)

    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    monkeypatch.setattr(api.resolve, "describe_under_cursor", fake_desc)
    client = TestClient(api.app)

    resp = client.get("/inspect", params={"x": 5, "y": 6})
    assert resp.status_code == 200
    assert recorded["coords"] == (5, 6)


def test_details_unknown_id():
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    client = TestClient(api.app)

    resp = client.get("/details", params={"id": "unknown"})
    assert resp.status_code == 404
    assert resp.json() == {"error": "id not found"}


def test_snapshot_unknown_id(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    # Patch capture to ensure no real screenshot is attempted if the code changes
    monkeypatch.setattr(api.screenshot, "capture", fake_capture)
    client = TestClient(api.app)

    resp = client.get("/snapshot", params={"id": "missing"})
    assert resp.status_code == 404
    assert resp.json() == {"error": "id not found"}


def test_snapshot_invalid_region(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    monkeypatch.setattr(api.screenshot, "capture", fake_capture)
    client = TestClient(api.app)

    resp = client.get("/snapshot", params={"region": "bad"})
    assert resp.status_code == 400
    assert resp.json() == {"error": "invalid region"}

