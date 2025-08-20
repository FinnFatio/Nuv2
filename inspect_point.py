import argparse
import resolve
from logger import setup
from cli import emit_cli_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Describe a point or current cursor")
    parser.add_argument("--point", type=str, help="x,y coordinates to inspect")
    parser.add_argument("--jsonl", action="store_true", help="Enable JSONL logging")
    parser.add_argument(
        "--rate-limit-hz", type=float, default=None, help="max log frequency"
    )
    args = parser.parse_args()
    setup(args.jsonl, rate_limit_hz=args.rate_limit_hz)
    if args.point:
        x, y = map(int, args.point.split(","))
        resolve.get_position = lambda: {"x": x, "y": y}
    info = resolve.describe_under_cursor()
    emit_cli_json(info, 0)


if __name__ == "__main__":  # pragma: no cover
    main()
