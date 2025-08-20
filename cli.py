import json
import sys
from typing import Any, Dict


def emit_cli_json(data: Dict[str, Any], code: int) -> None:
    """Print a single line of JSON to stdout and exit with ``code``.

    The JSON output is compact and deterministic, ensuring that stdout contains
    only the emitted JSON line. Any logging should go to stderr via the standard
    :mod:`logging` module.
    """
    sys.stdout.write(
        json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n"
    )
    sys.stdout.flush()
    raise SystemExit(code)
