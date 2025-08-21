from typing import Any, Dict, List

class _Output:
    DICT: int
    STRING: int

Output: _Output

tesseract_cmd: str

def image_to_data(image: Any, output_type: int = ...) -> Dict[str, List[str]]: ...
def image_to_string(image: Any) -> str: ...
