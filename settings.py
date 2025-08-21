import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

import mss
import PIL
import pytesseract

DEFAULTS: dict[str, Any] = {
    "OCR_LANG": "por+eng",
    "OCR_CFG": "--oem 3 --psm 6",
    "CAPTURE_WIDTH": 300,
    "CAPTURE_HEIGHT": 120,
    "UIA_THRESHOLD": 0.7,
    "TESSERACT_CMD": None,
    "CAPTURE_LOG_SAMPLE_RATE": 0.1,
    "CAPTURE_LOG_DEST": "stderr",
    "LOG_LEVEL": "info",
    "LOG_FORMAT": "text",
    "SNAPSHOT_MAX_AREA": 2_000_000,
    "SNAPSHOT_MAX_SIDE": 2000,
    "API_RATE_LIMIT_PER_MIN": 60,
    "API_CORS_ORIGINS": "",
}

CONFIG_SOURCES: dict[str, str] = {}


def _load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def load_settings() -> dict[str, Any]:
    cfg: dict[str, Any] = DEFAULTS.copy()
    origins: dict[str, str] = {key: "default" for key in DEFAULTS}
    json_path = Path("config.json")
    if json_path.exists():
        try:
            with json_path.open() as f:
                data = json.load(f)
            for key in DEFAULTS:
                if key in data:
                    cfg[key] = data[key]
                    origins[key] = "json"
        except Exception:
            pass
    env_path = Path(".env")
    if env_path.exists():
        try:
            env_data = _load_env_file(env_path)
            for key in DEFAULTS:
                if key in env_data:
                    cfg[key] = env_data[key]
                    origins[key] = ".env"
        except Exception:
            pass
    for key in DEFAULTS:
        if key in os.environ:
            cfg[key] = os.environ[key]
            origins[key] = "env"

    for key in (
        "CAPTURE_WIDTH",
        "CAPTURE_HEIGHT",
        "SNAPSHOT_MAX_AREA",
        "SNAPSHOT_MAX_SIDE",
        "API_RATE_LIMIT_PER_MIN",
    ):
        try:
            cfg[key] = int(cfg[key])
        except Exception:
            print(
                f"Invalid {key}={cfg[key]!r}, using default {DEFAULTS[key]!r}",
                file=sys.stderr,
            )
            cfg[key] = DEFAULTS[key]
            origins[key] = "default"

    for key in ("UIA_THRESHOLD", "CAPTURE_LOG_SAMPLE_RATE"):
        try:
            cfg[key] = float(cfg[key])
        except Exception:
            print(
                f"Invalid {key}={cfg[key]!r}, using default {DEFAULTS[key]!r}",
                file=sys.stderr,
            )
            cfg[key] = DEFAULTS[key]
            origins[key] = "default"

    cfg["CAPTURE_LOG_DEST"] = str(cfg["CAPTURE_LOG_DEST"])
    cfg["LOG_LEVEL"] = str(cfg["LOG_LEVEL"]).lower()
    if cfg["LOG_LEVEL"] not in {"debug", "info", "warning", "error", "critical"}:
        print(
            f"Invalid LOG_LEVEL={cfg['LOG_LEVEL']!r}, using default {DEFAULTS['LOG_LEVEL']!r}",
            file=sys.stderr,
        )
        cfg["LOG_LEVEL"] = DEFAULTS["LOG_LEVEL"]
        origins["LOG_LEVEL"] = "default"
    cfg["LOG_FORMAT"] = str(cfg["LOG_FORMAT"]).lower()
    if cfg["LOG_FORMAT"] not in {"text", "json"}:
        print(
            f"Invalid LOG_FORMAT={cfg['LOG_FORMAT']!r}, using default {DEFAULTS['LOG_FORMAT']!r}",
            file=sys.stderr,
        )
        cfg["LOG_FORMAT"] = DEFAULTS["LOG_FORMAT"]
        origins["LOG_FORMAT"] = "default"

    if cfg["CAPTURE_LOG_DEST"].startswith("file:"):
        path = Path(cfg["CAPTURE_LOG_DEST"][5:])
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not os.access(path.parent, os.W_OK):
                raise PermissionError
        except Exception:
            print(
                f"CAPTURE_LOG_DEST {cfg['CAPTURE_LOG_DEST']!r} not writable; using stderr",
                file=sys.stderr,
            )
            cfg["CAPTURE_LOG_DEST"] = "stderr"
            origins["CAPTURE_LOG_DEST"] = (
                "env" if "CAPTURE_LOG_DEST" in os.environ else "default"
            )

    version_stamp = {
        "python": platform.python_version(),
        "mss": getattr(mss, "__version__", None),
        "pillow": getattr(PIL, "__version__", None),
        "pytesseract": getattr(pytesseract, "__version__", None),
    }
    import logger as _logger

    _logger.setup(level=cfg["LOG_LEVEL"], fmt=cfg["LOG_FORMAT"])
    _logger.get_logger().debug(
        json.dumps({"config_digest": origins, "version_stamp": version_stamp})
    )
    global CONFIG_SOURCES
    CONFIG_SOURCES = origins
    return cfg


CONFIG = load_settings()
OCR_LANG = CONFIG["OCR_LANG"]
OCR_CFG = CONFIG["OCR_CFG"]
CAPTURE_WIDTH = CONFIG["CAPTURE_WIDTH"]
CAPTURE_HEIGHT = CONFIG["CAPTURE_HEIGHT"]
UIA_THRESHOLD = CONFIG["UIA_THRESHOLD"]
TESSERACT_CMD = CONFIG["TESSERACT_CMD"]
CAPTURE_LOG_SAMPLE_RATE = CONFIG["CAPTURE_LOG_SAMPLE_RATE"]
CAPTURE_LOG_DEST = CONFIG["CAPTURE_LOG_DEST"]
LOG_LEVEL = CONFIG["LOG_LEVEL"]
LOG_FORMAT = CONFIG["LOG_FORMAT"]
SNAPSHOT_MAX_AREA = CONFIG["SNAPSHOT_MAX_AREA"]
SNAPSHOT_MAX_SIDE = CONFIG["SNAPSHOT_MAX_SIDE"]
API_RATE_LIMIT_PER_MIN = CONFIG["API_RATE_LIMIT_PER_MIN"]
API_CORS_ORIGINS = CONFIG["API_CORS_ORIGINS"]
