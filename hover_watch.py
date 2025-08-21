import argparse
import time
from resolve import describe_under_cursor
from logger import setup, COMPONENT, get_logger
from cli_helpers import emit_cli_json_line
from settings import HOVER_WATCH_HZ, HOVER_WATCH_RUN_AS_ADMIN


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Poll describe_under_cursor at a fixed rate"
    )
    parser.add_argument(
        "--hz",
        type=float,
        default=HOVER_WATCH_HZ,
        help="polling frequency in Hertz",
    )
    parser.add_argument("--jsonl", action="store_true", help="Enable JSONL logging")
    parser.add_argument(
        "--rate-limit-hz", type=float, default=None, help="max log frequency"
    )
    args = parser.parse_args()
    setup(enable=args.jsonl, jsonl=args.jsonl, rate_limit_hz=args.rate_limit_hz)
    COMPONENT.set("cli")
    logger = get_logger()
    logger.info(
        "hover_watch starting",
        extra={"hz": args.hz, "run_as_admin": HOVER_WATCH_RUN_AS_ADMIN},
    )
    if HOVER_WATCH_RUN_AS_ADMIN:
        try:  # pragma: no cover - best effort
            logger.warning("run_as_admin requested but elevation not implemented")
        except Exception:
            logger.warning("run_as_admin requested but failed to elevate")
    delay = 1.0 / args.hz if args.hz > 0 else 0
    try:
        while True:
            info = describe_under_cursor()
            emit_cli_json_line(info)
            if delay:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
