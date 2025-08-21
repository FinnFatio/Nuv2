from typing import Any, Dict, List

class _Output:
    DICT: Any

class _Inner:
    tesseract_cmd: str

Output: _Output
pytesseract: _Inner

class TesseractError(Exception):
    ...

def image_to_data(
    image: Any,
    output_type: Any = ...,
    lang: str | None = ...,
    config: str | None = ...,
) -> Dict[str, List[str]]:
    ...
