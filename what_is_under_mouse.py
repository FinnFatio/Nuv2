import json
import ctypes

from resolve import describe_under_cursor


def main():
    """Collect and print information under the mouse cursor."""
    try:
        # Chamada evita deslocamento de coordenadas em ambientes com scaling >100%.
        ctypes.windll.user32.SetProcessDPIAware()
    except AttributeError:
        pass
    result = describe_under_cursor()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
