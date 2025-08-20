import json
import os
import sys
import platform
from pathlib import Path
import mss
import PIL
import pytesseract

DEFAULTS = {
    "OCR_LANG": "por+eng",
    "OCR_CFG": "--oem 3 --psm 6",
    "CAPTURE_WIDTH": 300,
    "CAPTURE_HEIGHT": 120,
    "UIA_THRESHOLD": 0.7,
    "TESSERACT_CMD": None,
    "CAPTURE_LOG_SAMPLE_RATE": 0.1,
    "CAPTURE_LOG_DEST": "stderr",
}


def _load_env_file(path: Path) -> dict:
    data = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def load_settings() -> dict:
    cfg = DEFAULTS.copy()
    origins = {key: "default" for key in DEFAULTS}
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

    for key in ("CAPTURE_WIDTH", "CAPTURE_HEIGHT"):
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
    version_stamp = {
        "python": platform.python_version(),
        "mss": getattr(mss, "__version__", None),
        "pillow": getattr(PIL, "__version__", None),
        "pytesseract": getattr(pytesseract, "__version__", None),
    }
    print(
        json.dumps({"config_digest": origins, "version_stamp": version_stamp}),
        file=sys.stderr,
    )
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
