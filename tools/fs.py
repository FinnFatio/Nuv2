from __future__ import annotations

from pathlib import Path
from typing import List


def _check_allow(path: Path, allow: List[str] | None) -> None:
    allow = allow or []
    if not any(Path(a) in path.parents or Path(a) == path for a in allow):
        raise PermissionError("path not allowed")


def list(path: str, allow: List[str] | None = None) -> List[str]:
    p = Path(path)
    _check_allow(p, allow)
    return [child.name for child in p.iterdir()]


def read(path: str, allow: List[str] | None = None, max_bytes: int = 100_000) -> str:
    p = Path(path)
    _check_allow(p, allow)
    data = p.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")
