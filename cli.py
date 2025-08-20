import json
from typing import Any, Dict


def emit_cli_json(data: Dict[str, Any], code: int) -> None:
    """Print a single line of JSON and exit with the given code."""
    print(json.dumps(data))
    raise SystemExit(code)
