import json
from resolve import describe_under_cursor


def main():
    result = describe_under_cursor()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
