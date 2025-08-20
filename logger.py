import json
import logging
import time
import uuid
from functools import wraps

ENABLED = False
SAMPLE_ID = uuid.uuid4().hex[:8]
RATE_LIMIT_INTERVAL = None
_LAST_LOG_TIME = 0.0
LOGGER = logging.getLogger("nuv2")
LOGGER.addHandler(logging.NullHandler())


def get_logger() -> logging.Logger:
    """Return the shared logger instance."""
    return LOGGER


def setup(jsonl: bool = False, rate_limit_hz: float | None = None) -> logging.Logger:
    """Configure logging and return the shared logger."""
    global ENABLED, RATE_LIMIT_INTERVAL, _LAST_LOG_TIME
    ENABLED = jsonl
    LOGGER.handlers.clear()
    LOGGER.propagate = False
    if jsonl:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)
        LOGGER.setLevel(logging.INFO)
    else:
        LOGGER.addHandler(logging.NullHandler())
    if rate_limit_hz and rate_limit_hz > 0:
        RATE_LIMIT_INTERVAL = 1.0 / rate_limit_hz
    else:
        RATE_LIMIT_INTERVAL = None
    _LAST_LOG_TIME = 0.0
    return LOGGER


def log(stage: str, start: float, error: str | None = None) -> None:
    """Emit a JSON log line with stage, elapsed_ms and error."""
    if not ENABLED:
        return
    now = time.time()
    if RATE_LIMIT_INTERVAL is not None:
        global _LAST_LOG_TIME
        if now - _LAST_LOG_TIME < RATE_LIMIT_INTERVAL:
            return
        _LAST_LOG_TIME = now
    elapsed_ms = int((now - start) * 1000)
    LOGGER.info(
        json.dumps(
            {
                "stage": stage,
                "elapsed_ms": elapsed_ms,
                "error": error,
                "sample_id": SAMPLE_ID,
            }
        )
    )


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
