from __future__ import annotations

from pathlib import Path
from typing import Dict, List

ALLOWED = [Path.cwd(), Path.cwd() / "experiments/llm_sandbox/assets"]


def _sanitize(text: str) -> str:
    from agent_local import _redact, _truncate

    return _truncate(_redact(text))


def list(path: str, recursive: bool | None = None, allow: List[str] | None = None) -> Dict:
    p = Path(path)
    allowed = ALLOWED + [Path(a) for a in (allow or [])]
    rp = p.resolve()
    if not any(base in rp.parents or base == rp for base in allowed):
        return {
            "kind": "error",
            "code": "forbidden_path",
            "message": "path not allowed",
            "hint": "",
        }
    try:
        if recursive:
            names = []
            for sub in p.rglob("*"):
                if sub.is_file() or sub.is_dir():
                    try:
                        names.append(str(sub.relative_to(p)))
                    except Exception:
                        names.append(str(sub))
        else:
            names = [c.name for c in p.iterdir()]
        return {"kind": "ok", "result": names}
    except Exception as e:
        return {
            "kind": "error",
            "code": "not_found",
            "message": str(e),
            "hint": "",
        }


def read(path: str, allow: List[str] | None = None, max_bytes: int = 100_000) -> Dict:
    p = Path(path)
    allowed = ALLOWED + [Path(a) for a in (allow or [])]
    rp = p.resolve()
    if not any(base in rp.parents or base == rp for base in allowed):
        return {
            "kind": "error",
            "code": "forbidden_path",
            "message": "path not allowed",
            "hint": "",
        }
    try:
        data = p.read_bytes()[:max_bytes]
        return {"kind": "ok", "result": _sanitize(data.decode("utf-8", "replace"))}
    except Exception as e:
        return {
            "kind": "error",
            "code": "not_found",
            "message": str(e),
            "hint": "",
        }


__all__ = ["list", "read"]
