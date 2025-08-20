import json
import logging
import os
import time
import uuid
from functools import wraps
import contextvars

ENABLED = False
SAMPLE_ID = uuid.uuid4().hex[:8]
RATE_LIMIT_INTERVAL = None
_LAST_LOG_TIME = 0.0
LOGGER = logging.getLogger("nuv2")
LOGGER.addHandler(logging.NullHandler())

# Context variables for rich logging
REQUEST_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
MONITOR: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "monitor", default=None
)
REGION: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "region", default=None
)
COMPONENT: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "component", default=None
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - simple
        base = {"level": record.levelname}
        try:
            data = json.loads(record.getMessage())
            if isinstance(data, dict):
                base.update(data)
            else:
                base["message"] = data
        except Exception:  # pragma: no cover - fallback
            base["message"] = record.getMessage()
        return json.dumps(base)


def get_logger() -> logging.Logger:
    """Return the shared logger instance."""
    return LOGGER


def setup(
    enable: bool = False,
    rate_limit_hz: float | None = None,
    level: str = "INFO",
    jsonl: bool | None = None,
    fmt: str | None = None,
) -> logging.Logger:
    """Configure logging and return the shared logger."""
    global ENABLED, RATE_LIMIT_INTERVAL, _LAST_LOG_TIME
    ENABLED = enable
    LOGGER.handlers.clear()
    LOGGER.propagate = False
    handler = logging.StreamHandler()

    # Determine format: explicit fmt overrides jsonl flag
    if fmt is None:
        fmt = "json" if jsonl else "text"
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    LOGGER.addHandler(handler)

    env_level = os.getenv("LOG_LEVEL")
    if env_level:
        level = env_level
    try:
        LOGGER.setLevel(getattr(logging, level.upper()))
    except Exception:  # pragma: no cover - invalid level
        LOGGER.setLevel(logging.INFO)
    if rate_limit_hz and rate_limit_hz > 0:
        RATE_LIMIT_INTERVAL = 1.0 / rate_limit_hz
    else:
        RATE_LIMIT_INTERVAL = None
    _LAST_LOG_TIME = 0.0
    return LOGGER


def log(
    stage: str,
    start: float,
    error: str | None = None,
    level: str = "INFO",
) -> None:
    """Emit a JSON log line with stage, elapsed_ms, error and context."""
    if not ENABLED:
        return
    now = time.time()
    if RATE_LIMIT_INTERVAL is not None:
        global _LAST_LOG_TIME
        if now - _LAST_LOG_TIME < RATE_LIMIT_INTERVAL:
            return
        _LAST_LOG_TIME = now
    elapsed_ms = int((now - start) * 1000)
    data = {
        "stage": stage,
        "elapsed_ms": elapsed_ms,
        "error": error,
        "sample_id": SAMPLE_ID,
    }
    req_id = REQUEST_ID.get()
    if req_id:
        data["request_id"] = req_id
    monitor = MONITOR.get()
    if monitor:
        data["monitor"] = monitor
    region = REGION.get()
    if region:
        data["region"] = region
    component = COMPONENT.get()
    if component:
        data["component"] = component
    try:
        lvl = getattr(logging, level.upper())
    except Exception:  # pragma: no cover - invalid level
        lvl = logging.INFO
    LOGGER.log(lvl, json.dumps(data))


def log_call(func):
    """Decorator to log function start, end and errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        log(f"{func.__name__}.start", start)
        try:
            result = func(*args, **kwargs)
        except Exception as e:  # pragma: no cover - re-raises original exception
            log(f"{func.__name__}.error", start, error=str(e))
            raise
        log(f"{func.__name__}.end", start)
        return result

    return wrapper
