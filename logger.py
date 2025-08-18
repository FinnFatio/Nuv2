import json
import logging
import time

ENABLED = False


def setup(jsonl: bool = False) -> None:
    """Configure logging if JSONL output is requested."""
    global ENABLED
    ENABLED = jsonl
    if jsonl:
        logging.basicConfig(level=logging.INFO, format="%(message)s")


def log(stage: str, start: float, error: str | None = None) -> None:
    """Emit a JSON log line with stage, elapsed_ms and error."""
    if not ENABLED:
        return
    elapsed_ms = int((time.time() - start) * 1000)
    logging.info(json.dumps({"stage": stage, "elapsed_ms": elapsed_ms, "error": error}))


def log_call(func):
    """Decorator to log function start, end and errors."""
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
