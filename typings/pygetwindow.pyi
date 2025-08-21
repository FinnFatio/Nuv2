from typing import List, Protocol

class Window(Protocol):
    left: int
    top: int
    width: int
    height: int
    title: str

def getActiveWindow() -> Window | None: ...
def getAllWindows() -> List[Window]: ...
