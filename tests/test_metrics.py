import os
import sys
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import api
import metrics


def test_metrics_endpoint(monkeypatch):
    metrics.reset()
    metrics.record_time("cursor", 10)
    metrics.record_time("cursor", 20)
    metrics.record_time("cursor", 30)
    metrics.record_fallback("used_ocr")
    metrics.record_request("/inspect", False)
    metrics.record_request("/inspect", True)
    client = TestClient(api.app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["latency_ms"]["cursor"]["p50"] == 20
    assert data["latency_ms"]["cursor"]["p95"] == 30
    assert data["fallbacks"]["used_ocr"] == 1
    assert data["error_rate"]["/inspect"] == 0.5
