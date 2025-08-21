from typing import Any, Dict, List, Protocol, Tuple

class _GrabResult(Protocol):
    size: Tuple[int, int]
    rgb: bytes

class mss:
    monitors: List[Dict[str, int]]
    def __init__(self) -> None: ...
    def grab(self, monitor: Dict[str, int]) -> _GrabResult: ...
    def close(self) -> None: ...
