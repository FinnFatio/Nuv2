import json
import sys
from typing import Any, Dict


API_VERSION = "v1"


def _dump_json(data: Dict[str, Any]) -> str:
    """Return a compact JSON representation of ``data``."""

    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def emit_cli_json(data: Dict[str, Any], code: int) -> None:
    """Emit a single JSON object following the API envelope contract.

    The ``data`` parameter represents either the success payload or the error
    object depending on ``code`` (``0`` for success). A ``SystemExit`` with the
    provided ``code`` is raised after writing the JSON line to stdout.
    """

    payload: Dict[str, Any] = {"ok": code == 0}
    if code == 0:
        payload["data"] = data
    else:
        payload["error"] = data
    payload["meta"] = {"version": API_VERSION}
    sys.stdout.buffer.write((_dump_json(payload) + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()
    raise SystemExit(code)


def emit_cli_json_line(data: Dict[str, Any]) -> None:
    """Write a single compact JSON line without exiting."""

    sys.stdout.buffer.write((_dump_json(data) + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()
