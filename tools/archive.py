from __future__ import annotations

import base64
import zipfile
from pathlib import Path, PurePosixPath
from typing import List

MAX_BYTES = 512_000
MAX_FILES = 200


def _check_allow(path: Path, allow: List[str] | None) -> None:
    allow = allow or []
    if not any(Path(a) in path.parents or Path(a) == path for a in allow):
        raise PermissionError("path not allowed")


def list(path: str, allow: List[str] | None = None) -> List[str]:
    p = Path(path)
    _check_allow(p, allow)
    with zipfile.ZipFile(p) as z:
        if len(z.infolist()) > MAX_FILES:
            raise ValueError("too_many_entries")
        return z.namelist()


def read(
    path: str,
    inner_path: str,
    allow: List[str] | None = None,
    max_bytes: int = MAX_BYTES,
) -> dict:
    p = Path(path)
    _check_allow(p, allow)
    with zipfile.ZipFile(p) as z:
        if len(z.infolist()) > MAX_FILES:
            raise ValueError("too_many_entries")
        pp = PurePosixPath(inner_path)
        if pp.is_absolute() or ".." in pp.parts:
            raise ValueError("bad_path")
        info = z.getinfo(inner_path)
        ratio = (info.file_size or 1) / max(info.compress_size or 1, 1)
        if ratio > 1000 or info.file_size > max_bytes:
            raise ValueError("too_big")
        data = z.read(info)[:max_bytes]
    return {
        "inner_path": inner_path,
        "bytes_b64": base64.b64encode(data).decode("ascii"),
    }
