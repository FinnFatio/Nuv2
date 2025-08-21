from typing import Any, Dict

class Output:
    DICT: Any

class TesseractError(Exception): ...

pytesseract: Any

def image_to_data(
    image: Any, output_type: Any = ..., lang: str | None = ..., config: str | None = ...
) -> Dict[str, Any]: ...
