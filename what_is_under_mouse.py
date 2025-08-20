import argparse
import ctypes

from resolve import describe_under_cursor
from logger import setup
from cli import emit_cli_json


def main(argv=None):
    """Collect and print information under the mouse cursor."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", action="store_true", help="Enable JSONL logging")
    parser.add_argument(
        "--rate-limit-hz", type=float, default=None, help="max log frequency"
    )
    args = parser.parse_args(argv)

    setup(args.jsonl, rate_limit_hz=args.rate_limit_hz)

    try:
        # Chamada evita deslocamento de coordenadas em ambientes com scaling >100%.
        ctypes.windll.user32.SetProcessDPIAware()
    except AttributeError:
        pass
    result = describe_under_cursor()
    emit_cli_json(result, 0)


if __name__ == "__main__":
    main()
