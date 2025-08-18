import argparse
import json
import resolve


def main() -> None:
    parser = argparse.ArgumentParser(description="Describe a point or current cursor")
    parser.add_argument("--point", type=str, help="x,y coordinates to inspect")
    args = parser.parse_args()
    if args.point:
        x, y = map(int, args.point.split(","))
        resolve.get_position = lambda: {"x": x, "y": y}
    info = resolve.describe_under_cursor()
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
