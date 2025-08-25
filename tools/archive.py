from __future__ import annotations

import base64
import zipfile
from pathlib import Path, PurePosixPath
from typing import Dict

from . import fs

MAX_BYTES = 512_000
MAX_FILES = 200


def list(path: str, allow: list[str] | None = None) -> Dict:
    p = Path(path)
    rp = p.resolve()
    allowed = fs.ALLOWED + [Path(a) for a in (allow or [])]  # type: ignore[attr-defined]
    if not any(base in rp.parents or base == rp for base in allowed):
        return {
            "kind": "error",
            "code": "forbidden_path",
            "message": "path not allowed",
            "hint": "",
        }
    try:
        with zipfile.ZipFile(p) as z:
            if len(z.infolist()) > MAX_FILES:
                return {
                    "kind": "error",
                    "code": "bad_args",
                    "message": "too_many_entries",
                    "hint": "",
                }
            return {"kind": "ok", "result": z.namelist()}
    except Exception as e:
        return {"kind": "error", "code": "not_found", "message": str(e), "hint": ""}


def read(path: str, inner_path: str, allow: list[str] | None = None) -> Dict:
    p = Path(path)
    rp = p.resolve()
    allowed = fs.ALLOWED + [Path(a) for a in (allow or [])]  # type: ignore[attr-defined]
    if not any(base in rp.parents or base == rp for base in allowed):
        return {
            "kind": "error",
            "code": "forbidden_path",
            "message": "path not allowed",
            "hint": "",
        }
    try:
        with zipfile.ZipFile(p) as z:
            if len(z.infolist()) > MAX_FILES:
                return {
                    "kind": "error",
                    "code": "too_many_entries",
                    "message": "archive too large",
                    "hint": "",
                }
            pp = PurePosixPath(inner_path)
            if pp.is_absolute() or ".." in pp.parts:
                return {
                    "kind": "error",
                    "code": "bad_args",
                    "message": "bad_path",
                    "hint": "",
                }
            info = z.getinfo(inner_path)
            ratio = (info.file_size or 1) / max(info.compress_size or 1, 1)
            if ratio > 1000 or info.file_size > MAX_BYTES:
                return {
                    "kind": "error",
                    "code": "bad_args",
                    "message": "too_big",
                    "hint": "",
                }
            data = z.read(info)[:MAX_BYTES]
            return {
                "kind": "ok",
                "result": {
                    "inner_path": inner_path,
                    "bytes_b64": base64.b64encode(data).decode("ascii"),
                },
            }
    except Exception as e:
        return {"kind": "error", "code": "not_found", "message": str(e), "hint": ""}


__all__ = ["list", "read"]
