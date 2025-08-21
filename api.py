from __future__ import annotations

from typing import (
    Any,
    Dict,
    Callable,
    Awaitable,
    Deque,
    DefaultDict,
    ParamSpec,
    TypeVar,
    cast,
)
import io
import sys
from contextvars import Token

# Ensure standard library modules have priority over local names like inspect.py
if "" in sys.path:
    sys.path.remove("")
    sys.path.append("")
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict, deque
import time
import resolve
import screenshot
from screenshot import ERROR_CODE_MAP
from primitives import Bounds, ErrorEnvelope, ErrorInfo, OkEnvelope
from logger import setup, log_call as _log_call, REQUEST_ID, COMPONENT
import metrics
import uuid
from dispatcher import dispatch
from registry import REGISTRY
import tools
from settings import (
    SNAPSHOT_MAX_AREA,
    SNAPSHOT_MAX_SIDE,
    API_RATE_LIMIT_PER_MIN,
    API_CORS_ORIGINS,
    TRUST_PROXY,
    API_KEY,
)

tools.register_all_tools()

P = ParamSpec("P")
T = TypeVar("T")
log_call = cast(Callable[[Callable[P, T]], Callable[P, T]], _log_call)

# Enable JSON logging similar to CLI tools
setup(enable=True, jsonl=True)
COMPONENT.set("api")

app = FastAPI()

if API_CORS_ORIGINS:
    origins = [o.strip() for o in API_CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

API_VERSION = "v1"
MAX_TOOL_CALL_BYTES = 256 * 1024


def ok_response(data: Dict[str, Any], version: str = API_VERSION) -> OkEnvelope:
    return {"ok": True, "data": data, "meta": {"version": version}}


def error_response(
    code: str, message: str, version: str = API_VERSION
) -> ErrorEnvelope:
    err: ErrorInfo = {"code": code, "message": message}
    return {"ok": False, "error": err, "meta": {"version": version}}


def _require_api_key(request: Request) -> JSONResponse | None:
    if not API_KEY:
        return None
    if request.headers.get("X-API-Key") != API_KEY:
        return JSONResponse(
            error_response("unauthorized", "invalid api key"), status_code=401
        )
    return None


ELEMENT_CACHE: Dict[str, Dict[str, Any]] = {}
BOUNDS_CACHE: Dict[str, Bounds] = {}

# Janela deslizante de timestamps por IP para rate limit (últimos 60s)
# Limita o deque para evitar crescimento descontrolado sob carga anômala
_REQUEST_LOG: DefaultDict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=120))


@app.middleware("http")
async def add_request_id_and_rate_limit(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    token: Token[str] = REQUEST_ID.set(request_id)
    ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if TRUST_PROXY and forwarded_for:
        # X-Forwarded-For may contain a comma separated list of addresses;
        # the client IP is the first one in the list.
        ip = forwarded_for.split(",", 1)[0].strip()
    now = time.time()
    dq = _REQUEST_LOG[ip]
    while dq and now - dq[0] > 60:
        dq.popleft()
    if len(dq) >= API_RATE_LIMIT_PER_MIN:
        metrics.record_request(request.url.path, 429)
        envelope = error_response("rate_limit", "rate limit exceeded")
        response = JSONResponse(envelope, status_code=429)
        response.headers["Retry-After"] = "60"
        response.headers["X-Request-Id"] = request_id
        REQUEST_ID.reset(token)
        return response
    dq.append(now)
    try:
        response = await call_next(request)
        metrics.record_request(request.url.path, response.status_code)
        response.headers["X-Request-Id"] = request_id
        return response
    finally:
        REQUEST_ID.reset(token)


@app.get("/inspect")
@log_call
def inspect(
    x: int | None = Query(default=None), y: int | None = Query(default=None)
) -> JSONResponse:
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
    return JSONResponse(ok_response(info))


@app.get("/details")
@log_call
def details(id: str = Query(...)) -> JSONResponse:
    """Return cached element details for the given control or window ID."""
    element = ELEMENT_CACHE.get(id)
    if not element:
        return JSONResponse(
            error_response("id_not_found", "id not found"), status_code=404
        )
    return JSONResponse(ok_response(element))


@app.get("/snapshot")
@log_call
def snapshot(id: str | None = None, region: str | None = None) -> Response:
    """Return a PNG screenshot by element ID or explicit region."""
    if (id is None) == (region is None):
        return JSONResponse(
            error_response("missing_id_or_region", "provide id or region"),
            status_code=400,
        )
    if id is not None:
        bounds = BOUNDS_CACHE.get(id)
        if not bounds:
            return JSONResponse(
                error_response("id_not_found", "id not found"), status_code=404
            )
        region_tuple = (
            bounds["left"],
            bounds["top"],
            bounds["right"],
            bounds["bottom"],
        )
    else:
        assert region is not None
        try:
            x, y, w, h = map(int, region.split(","))
        except Exception:
            return JSONResponse(
                error_response("invalid_region", "invalid region"), status_code=400
            )
        if w * h > SNAPSHOT_MAX_AREA or w > SNAPSHOT_MAX_SIDE or h > SNAPSHOT_MAX_SIDE:
            return JSONResponse(
                error_response("region_too_large", "region too large"),
                status_code=400,
            )
        region_tuple = (x, y, x + w, y + h)
    try:
        img = screenshot.capture(region_tuple)
    except ValueError as e:
        msg = str(e)
        code = ERROR_CODE_MAP.get(msg)
        if code is None:
            code = "bad_region"
        return JSONResponse(error_response(code, msg), status_code=400)
    except Exception as e:  # pragma: no cover - unexpected capture failure
        code = ERROR_CODE_MAP.get(str(e), "capture_failed")
        return JSONResponse(error_response(code, str(e)), status_code=500)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    resp = StreamingResponse(buf, media_type="image/png")
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/healthz")
@app.head("/healthz")
@log_call
def healthz() -> JSONResponse:
    """Return basic screenshot health information."""
    return JSONResponse(ok_response(screenshot.health_check()))


@app.get("/metrics")
@log_call
def get_metrics() -> JSONResponse:
    """Return aggregated latency, fallback and error information."""
    return JSONResponse(ok_response(metrics.summary()))


class ToolCallModel(BaseModel):  # type: ignore[misc]
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)


@app.get("/v1/tools.list")
def tools_list(request: Request) -> JSONResponse:
    auth = _require_api_key(request)
    if auth:
        return auth
    cards = [
        {
            "name": spec["name"],
            "version": spec["version"],
            "summary": spec["summary"],
            "safety": spec["safety"],
            "enabled_in_safe_mode": spec.get("enabled_in_safe_mode", False),
        }
        for spec in REGISTRY.values()
    ]
    return JSONResponse(ok_response({"tools": cards}))


@app.post("/v1/tools.call")
def tools_call(body: ToolCallModel, request: Request) -> JSONResponse:
    req_id = REQUEST_ID.get()
    auth = _require_api_key(request)
    if auth:
        auth.headers["X-Request-Id"] = req_id
        return auth
    if int(request.headers.get("content-length", "0")) > MAX_TOOL_CALL_BYTES:
        r = JSONResponse(
            error_response("bad_args", "request too large"), status_code=400
        )
        r.headers["X-Request-Id"] = req_id
        return r
    res = dispatch({"name": body.name, "args": body.args}, request_id=req_id)
    http = (
        200
        if res["kind"] == "ok"
        else (
            429
            if res.get("code") == "rate_limit"
            else 403
            if res.get("code") == "forbidden"
            else 400
            if res.get("code") in {"bad_args", "not_found"}
            else 504
            if res.get("code") == "timeout"
            else 500
        )
    )
    j = (
        res
        if res["kind"] == "ok"
        else error_response(res.get("code", "tool_error"), res.get("error", ""))
    )
    r = JSONResponse(j, status_code=http)
    r.headers["X-Request-Id"] = req_id
    return r
