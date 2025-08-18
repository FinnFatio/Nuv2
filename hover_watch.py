import argparse
import json
import time
from resolve import describe_under_cursor
from logger import setup


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll describe_under_cursor at a fixed rate")
    parser.add_argument("--hz", type=float, default=1.0, help="polling frequency in Hertz")
    parser.add_argument("--jsonl", action="store_true", help="Enable JSONL logging")
    args = parser.parse_args()
    setup(args.jsonl)
    delay = 1.0 / args.hz if args.hz > 0 else 0
    try:
        while True:
            info = describe_under_cursor()
            print(json.dumps(info, ensure_ascii=False))
            if delay:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
