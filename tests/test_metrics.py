import sys
import types
from fastapi.testclient import TestClient
import metrics

pytesseract_module = types.ModuleType("pytesseract")
pytesseract_module.image_to_string = lambda *a, **k: ""
sys.modules["pytesseract"] = pytesseract_module

for k in list(sys.modules):
    if k.startswith("PIL"):
        sys.modules.pop(k)


def get_api():
    import api as _api

    return _api


def test_metrics_endpoint(monkeypatch):
    api = get_api()
    metrics.reset()
    metrics.record_time("cursor", 10)
    metrics.record_time("cursor", 20)
    metrics.record_time("cursor", 30)
    metrics.record_fallback("used_ocr")
    metrics.record_request("/inspect", 200)
    metrics.record_request("/inspect", 429)
    client = TestClient(api.app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["latency_ms"]["cursor"]["p50"] == 20
    assert data["latency_ms"]["cursor"]["p95"] == 30
    assert data["fallbacks"]["used_ocr"] == 1
    assert data["error_rate"]["/inspect"] == 0.5
    assert data["status_total"]["/inspect"]["429"] == 1
    assert data["rate_limited_total"] == 1
