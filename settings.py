import json
import os
from pathlib import Path

DEFAULTS = {
    "OCR_LANG": "por+eng",
    "OCR_CFG": "--oem 3 --psm 6",
    "CAPTURE_WIDTH": 300,
    "CAPTURE_HEIGHT": 120,
    "UIA_THRESHOLD": 0.7,
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
    json_path = Path("config.json")
    if json_path.exists():
        try:
            with json_path.open() as f:
                data = json.load(f)
            for key in DEFAULTS:
                if key in data:
                    cfg[key] = data[key]
        except Exception:
            pass
    env_path = Path(".env")
    if env_path.exists():
        try:
            env_data = _load_env_file(env_path)
            for key in DEFAULTS:
                if key in env_data:
                    cfg[key] = env_data[key]
        except Exception:
            pass
    for key in DEFAULTS:
        if key in os.environ:
            cfg[key] = os.environ[key]
    cfg["CAPTURE_WIDTH"] = int(cfg["CAPTURE_WIDTH"])
    cfg["CAPTURE_HEIGHT"] = int(cfg["CAPTURE_HEIGHT"])
    cfg["UIA_THRESHOLD"] = float(cfg["UIA_THRESHOLD"])
    return cfg

CONFIG = load_settings()
OCR_LANG = CONFIG["OCR_LANG"]
OCR_CFG = CONFIG["OCR_CFG"]
CAPTURE_WIDTH = CONFIG["CAPTURE_WIDTH"]
CAPTURE_HEIGHT = CONFIG["CAPTURE_HEIGHT"]
UIA_THRESHOLD = CONFIG["UIA_THRESHOLD"]
