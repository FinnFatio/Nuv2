import argparse
import json
import ctypes

from resolve import describe_under_cursor
from logger import setup


def main(argv=None):
    """Collect and print information under the mouse cursor."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", action="store_true", help="Enable JSONL logging")
    args = parser.parse_args(argv)

    setup(args.jsonl)

    try:
        # Chamada evita deslocamento de coordenadas em ambientes com scaling >100%.
        ctypes.windll.user32.SetProcessDPIAware()
    except AttributeError:
        pass
    result = describe_under_cursor()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
