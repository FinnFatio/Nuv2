from __future__ import annotations

from typing import (
    Any,
    Dict,
    Literal,
    NotRequired,
    Protocol,
    Required,
    Tuple,
    TypedDict,
)


class Point(TypedDict):
    x: int
    y: int


class MonitorDict(TypedDict):
    left: int
    top: int
    width: int
    height: int


class Bounds(TypedDict):
    left: Required[int]
    top: Required[int]
    right: Required[int]
    bottom: Required[int]
    monitor: NotRequired[str]


class UIAWindowInfo(TypedDict, total=False):
    handle: int
    active: bool
    pid: int
    title: str
    app_path: str
    bounds: Bounds


class UIAElementInfo(TypedDict, total=False):
    control_type: str
    role: str
    name: str
    value: str
    enabled: bool
    offscreen: bool
    bounds: Bounds


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


__all__ = [
    "Point",
    "Bounds",
    "UIAWindowInfo",
    "UIAElementInfo",
    "GrabResult",
    "ErrorInfo",
    "ErrorEnvelope",
    "OkEnvelope",
]
