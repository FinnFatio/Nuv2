from __future__ import annotations

from typing import (
    Any,
    Dict,
    Literal,
    Protocol,
    Tuple,
    TypedDict,
)


class Point(TypedDict):
    x: int
    y: int


class Bounds(TypedDict, total=False):
    left: int
    top: int
    right: int
    bottom: int
    monitor: str


class GrabResult(Protocol):
    size: Tuple[int, int]
    rgb: bytes


class ErrorInfo(TypedDict):
    code: str
    message: str


class ErrorEnvelope(TypedDict):
    ok: Literal[False]
    error: ErrorInfo
    meta: Dict[str, Any]


class OkEnvelope(TypedDict):
    ok: Literal[True]
    data: Dict[str, Any]
    meta: Dict[str, Any]
