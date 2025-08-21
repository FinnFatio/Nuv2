import json
import sys
import types
from fastapi.testclient import TestClient

pytesseract_module = types.ModuleType("pytesseract")
pytesseract_module.image_to_string = lambda *a, **k: ""
sys.modules["pytesseract"] = pytesseract_module

for k in list(sys.modules):
    if k.startswith("PIL"):
        sys.modules.pop(k)


def get_api_logger():
    import api as _api
    import logger as _logger

    return _api, _logger


api, logger = get_api_logger()


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
    monkeypatch.setattr(
        api.resolve, "describe_under_cursor", fake_describe_under_cursor
    )
    monkeypatch.setattr(api.screenshot, "capture", fake_capture)
    client = TestClient(api.app)

    resp = client.get("/inspect")
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id")
    data = resp.json()
    assert data["ok"] is True
    assert data["meta"]["version"] == "v1"
    assert data["data"]["control_id"] == "c1"
    assert data["data"]["window_id"] == "w1"

    resp = client.get("/details", params={"id": "c1"})
    assert resp.status_code == 200
    assert resp.json()["data"]["patterns"] == ["ValuePattern"]

    resp = client.get("/snapshot", params={"region": "0,0,1,1"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["cache-control"] == "no-store"

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
    data = resp.json()["data"]
    assert data["control_id"] == "c1"
    assert data["window_id"] == "w1"


def test_details_unknown_id():
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    client = TestClient(api.app)

    resp = client.get("/details", params={"id": "unknown"})
    assert resp.status_code == 404
    assert resp.json() == {
        "ok": False,
        "error": {"code": "id_not_found", "message": "id not found"},
        "meta": {"version": "v1"},
    }


def test_snapshot_unknown_id(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    # Patch capture to ensure no real screenshot is attempted if the code changes
    monkeypatch.setattr(api.screenshot, "capture", fake_capture)
    client = TestClient(api.app)

    resp = client.get("/snapshot", params={"id": "missing"})
    assert resp.status_code == 404
    assert resp.json() == {
        "ok": False,
        "error": {"code": "id_not_found", "message": "id not found"},
        "meta": {"version": "v1"},
    }


def test_snapshot_invalid_region(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    monkeypatch.setattr(api.screenshot, "capture", fake_capture)
    client = TestClient(api.app)

    resp = client.get("/snapshot", params={"region": "bad"})
    assert resp.status_code == 400
    assert resp.json() == {
        "ok": False,
        "error": {"code": "invalid_region", "message": "invalid region"},
        "meta": {"version": "v1"},
    }


def test_snapshot_missing_id_and_region():
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    client = TestClient(api.app)
    resp = client.get("/snapshot")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "missing_id_or_region"


def test_snapshot_both_id_and_region(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    monkeypatch.setattr(api.screenshot, "capture", fake_capture)
    api.BOUNDS_CACHE["c1"] = {"left": 0, "top": 0, "right": 1, "bottom": 1}
    client = TestClient(api.app)
    resp = client.get("/snapshot", params={"id": "c1", "region": "0,0,1,1"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "missing_id_or_region"


def test_snapshot_capture_error_map(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()

    def boom(region):
        raise ValueError("No active window found")

    monkeypatch.setattr(api.screenshot, "capture", boom)
    client = TestClient(api.app)
    resp = client.get("/snapshot", params={"region": "0,0,1,1"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "no_active_window"


def test_snapshot_region_too_large(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    monkeypatch.setattr(api.screenshot, "capture", fake_capture)
    monkeypatch.setattr(api, "SNAPSHOT_MAX_AREA", 4)
    monkeypatch.setattr(api, "SNAPSHOT_MAX_SIDE", 3)
    client = TestClient(api.app)
    resp = client.get("/snapshot", params={"region": "0,0,3,3"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "region_too_large"


def test_healthz_endpoint(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    monkeypatch.setattr(api.screenshot, "health_check", lambda: {"ok": True})
    client = TestClient(api.app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["data"] == {"ok": True}


def test_healthz_head(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    monkeypatch.setattr(api.screenshot, "health_check", lambda: {"ok": True})
    client = TestClient(api.app)
    resp = client.head("/healthz")
    assert resp.status_code == 200
    assert resp.content == b""


def test_rate_limit(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    monkeypatch.setattr(
        api.resolve, "describe_under_cursor", fake_describe_under_cursor
    )
    monkeypatch.setattr(api, "API_RATE_LIMIT_PER_MIN", 2)
    api._REQUEST_LOG.clear()
    client = TestClient(api.app)
    client.get("/inspect")
    client.get("/inspect")
    resp = client.get("/inspect")
    assert resp.status_code == 429
    data = resp.json()
    assert data["error"]["code"] == "rate_limit"
    assert resp.headers["Retry-After"] == "60"


def test_inspect_tesseract_error(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()

    def fake_get_position():
        return {"x": 0, "y": 0}

    def fake_element_info(x, y):
        return ({}, {"bounds": {}}, "", 0.0)

    def fake_capture_around(pos, bounds=None):
        return ("img", None)

    def raise_ocr(img):  # pragma: no cover - error path
        raise RuntimeError("tesseract_failed")

    monkeypatch.setattr(api.resolve, "get_position", fake_get_position)
    monkeypatch.setattr(api.resolve, "get_element_info", fake_element_info)
    monkeypatch.setattr(api.resolve, "capture_around", fake_capture_around)
    monkeypatch.setattr(api.resolve, "extract_text", raise_ocr)

    client = TestClient(api.app)
    resp = client.get("/inspect")
    assert resp.status_code == 200
    assert resp.json()["data"]["errors"]["extract_text"] == "tesseract_failed"


def test_request_id_logged(monkeypatch):
    api.ELEMENT_CACHE.clear()
    api.BOUNDS_CACHE.clear()
    monkeypatch.setattr(
        api.resolve, "describe_under_cursor", fake_describe_under_cursor
    )

    class CaptureLogger:
        def __init__(self):
            self.last = None

        def log(self, level, msg, *args, **kwargs):
            self.last = msg

    cap = CaptureLogger()
    monkeypatch.setattr(logger, "get_logger", lambda: cap)
    monkeypatch.setattr(logger, "LOGGER", cap)

    client = TestClient(api.app)
    rid = "fixed-id"
    resp = client.get("/inspect", headers={"X-Request-Id": rid})
    assert resp.status_code == 200
    data = json.loads(cap.last)
    assert data["request_id"] == rid
