from __future__ import annotations

import json
import os
import re
import uuid
import time
import random
import logging
from typing import Any, Dict, List, Tuple, TypedDict, Protocol, Callable

import requests
from typing import cast

from dispatcher import dispatch
from registry import get_tool
import settings
import logger as _logger
import metrics

MAX_TOOL_RESULT_CHARS = 1000
MAX_TOOL_RESULT_TOKENS = 512



class ToolCall(TypedDict, total=False):
    name: str
    args: Dict[str, Any]
    id: str


class Message(TypedDict, total=False):
    role: str
    content: str
    name: str
    tool_call_id: str


Messages = List[Message]


class LLMFn(Protocol):
    def __call__(
        self,
        messages: Messages,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        ...

_TOOLCALL_RE = re.compile(r"<toolcall>(.*?)</toolcall>", re.DOTALL)


def _truncate(
    text: str,
    char_limit: int = MAX_TOOL_RESULT_CHARS,
    token_limit: int = MAX_TOOL_RESULT_TOKENS,
) -> str:
    tokens = text.split()
    if len(tokens) > token_limit:
        removed = len(tokens) - token_limit
        text = " ".join(tokens[:token_limit]) + f"... [truncated {removed} tokens]"
    if len(text) > char_limit:
        return text[:char_limit] + "..." + f" [truncated {len(text) - char_limit} chars]"
    return text


def _parse_toolcalls(content: str) -> Tuple[str, List[ToolCall]]:
    toolcalls: List[ToolCall] = []

    # Support JSON formats like {"tool_calls": [...]}
    try:
        data = json.loads(content)
    except Exception:
        data = None
    if isinstance(data, dict):
        container: Any | None = None
        if isinstance(data.get("tool_calls"), list):
            container = data["tool_calls"]
        elif isinstance(data.get("tools"), list):
            container = data["tools"]
        if container is not None:
            for item in container:
                if not isinstance(item, dict):
                    continue
                if "function" in item:
                    func = item.get("function", {}) or {}
                    name = str(func.get("name", ""))
                    args_raw = func.get("arguments", {})
                    try:
                        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    except Exception:
                        args = {}
                    toolcalls.append({"name": name, "args": args, "id": item.get("id", "")})
                else:
                    name = str(item.get("name", ""))
                    args = item.get("args", {})
                    toolcalls.append({"name": name, "args": args, "id": item.get("id", "")})
            return str(data.get("content", "")).strip(), toolcalls

    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        data: Dict[str, Any] | None = None
        try:
            data = json.loads(inner)
        except Exception:
            fixed = inner.replace("'", '"')
            fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
            try:
                data = json.loads(fixed)
            except Exception:
                return ""
        if isinstance(data, dict) and "name" in data:
            toolcalls.append(
                {
                    "name": data.get("name", ""),
                    "args": data.get("args", {}),
                    "id": data.get("id", ""),
                }
            )
        return ""

    cleaned = _TOOLCALL_RE.sub(repl, content)
    return cleaned.strip(), toolcalls


def _shrink(messages: Messages, max_msgs: int = 20) -> Messages:
    if len(messages) <= max_msgs:
        return messages
    kept: Messages = [m for m in messages if m["role"] == "user"][:1]
    kept += messages[-(max_msgs - 1) :]
    kept.insert(0, {"role": "system", "content": "[context shrunk]"})
    return kept


def _default_llm_backend(
    endpoint: str | None = None, model: str | None = None
) -> LLMFn:
    endpoint = (endpoint or os.getenv("LLM_ENDPOINT") or "").strip()
    model = (model or os.getenv("LLM_MODEL") or "").strip()
    if not endpoint or not model:
        raise RuntimeError("LLM_ENDPOINT e LLM_MODEL obrigatórios")

    def _chat(
        messages: Messages,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        for attempt, timeout in enumerate((60, 90, 120), 1):
            try:
                payload: Dict[str, Any] = {"model": model, "messages": messages}
                if max_tokens is not None:
                    payload["max_tokens"] = max_tokens
                if temperature is not None:
                    payload["temperature"] = temperature
                resp = requests.post(endpoint, json=payload, timeout=timeout)
                resp.raise_for_status()
                data = cast(Dict[str, Any], resp.json())
                return str(data["choices"][0]["message"]["content"])
            except Exception as e:  # pragma: no cover - network
                if attempt == 3:
                    raise RuntimeError(f"LLM request failed: {e}") from e
                time.sleep(attempt + random.uniform(0, 0.5))
        return ""

    return _chat


class Agent:
    def __init__(
        self,
        *,
        llm: LLMFn | None = None,
        max_tools: int = 3,
        safe_mode: bool | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        log: logging.Logger | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.llm: LLMFn = llm or _default_llm_backend(endpoint=endpoint, model=model)
        self.max_tools = max_tools
        self.safe_mode = settings.SAFE_MODE if safe_mode is None else safe_mode
        self.log = log or _logger.get_logger()
        self.clock = clock or time.time

    def chat(self, prompt: str) -> str:
        messages: Messages = [{"role": "user", "content": prompt}]
        tool_calls_used = 0
        conversation_id = str(uuid.uuid4())
        turn = 0
        failure_streak = 0

        last_tool = ""
        while tool_calls_used < self.max_tools:
            turn += 1
            start_call = self.clock()
            res = self.llm(messages, max_tokens=256, temperature=0.2)
            if isinstance(res, tuple):
                reply, usage = res
            else:
                reply, usage = res, None
            elapsed = self.clock() - start_call
            if usage and isinstance(usage.get("completion_tokens"), int):
                tokens = usage.get("completion_tokens", 0)
                tps = tokens / elapsed if elapsed > 0 else float("inf")
                metrics.record_gauge("tokens_per_sec", tps)
                self.log.info(
                    json.dumps(
                        {
                            "event": "llm_call",
                            "elapsed_ms": int(elapsed * 1000),
                            "tokens": tokens,
                            "prompt_tokens": usage.get("prompt_tokens"),
                            "tokens_per_sec": tps,
                            "conversation_id": conversation_id,
                            "turn": turn,
                            "safe_mode": self.safe_mode,
                        }
                    )
                )
            else:
                approx_tokens = len(reply.split())
                tps = approx_tokens / elapsed if elapsed > 0 else float("inf")
                metrics.record_gauge("tokens_per_sec", tps)
                self.log.info(
                    json.dumps(
                        {
                            "event": "llm_call",
                            "elapsed_ms": int(elapsed * 1000),
                            "approx_tokens": approx_tokens,
                            "approx_tokens_per_sec": tps,
                            "conversation_id": conversation_id,
                            "turn": turn,
                            "safe_mode": self.safe_mode,
                        }
                    )
                )
            text, toolcalls = _parse_toolcalls(reply)
            messages.append({"role": "assistant", "content": text})
            if not toolcalls:
                failure_streak = 0
                return text.strip()
            for tc in toolcalls:
                if tool_calls_used >= self.max_tools:
                    self.log.info(
                        json.dumps(
                            {
                                "event": "tool_limit_reached",
                                "limit": self.max_tools,
                                "conversation_id": conversation_id,
                                "turn": turn,
                                "request_id": None,
                                "tool_call_id": None,
                                "safe_mode": self.safe_mode,
                            }
                        )
                    )
                    break
                name = tc.get("name", "")
                if name != last_tool:
                    failure_streak = 0
                    last_tool = name
                tool = get_tool(name)
                tool_call_id = tc.get("id") or str(uuid.uuid4())
                request_id = str(uuid.uuid4())
                if tool is None:
                    failure_streak += 1
                    self.log.warning(
                        json.dumps(
                            {
                                "event": "unknown_tool",
                                "name": name,
                                "conversation_id": conversation_id,
                                "turn": turn,
                                "request_id": request_id,
                                "tool_call_id": tool_call_id,
                                "safe_mode": self.safe_mode,
                            }
                        )
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "name": name,
                            "tool_call_id": tool_call_id,
                            "content": f"tool {name} unavailable",
                        }
                    )
                    if failure_streak >= 3:
                        self.log.warning(
                            json.dumps(
                                {
                                    "event": "circuit_breaker",
                                    "conversation_id": conversation_id,
                                    "turn": turn,
                                    "safe_mode": self.safe_mode,
                                }
                            )
                        )
                        return "tool failures exceeded"
                    continue
                if self.safe_mode and not tool.get("enabled_in_safe_mode", False):
                    self.log.warning(
                        json.dumps(
                            {
                                "event": "tool_disabled_safe_mode",
                                "name": name,
                                "conversation_id": conversation_id,
                                "turn": turn,
                                "request_id": request_id,
                                "tool_call_id": tool_call_id,
                                "safe_mode": self.safe_mode,
                            }
                        )
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "name": name,
                            "tool_call_id": tool_call_id,
                            "content": f"tool {name} disabled in safe_mode",
                        }
                    )
                    continue
                args = tc.get("args", {})
                schema = tool.get("schema") if isinstance(tool, dict) else None
                if schema:
                    missing = [k for k in schema.get("required", []) if k not in args]
                    if missing:
                        failure_streak += 1
                        self.log.warning(
                            json.dumps(
                                {
                                    "event": "invalid_tool_args",
                                    "name": name,
                                    "missing": missing,
                                    "conversation_id": conversation_id,
                                    "turn": turn,
                                    "request_id": request_id,
                                    "tool_call_id": tool_call_id,
                                    "safe_mode": self.safe_mode,
                                }
                            )
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "name": name,
                                "tool_call_id": tool_call_id,
                                "content": "missing args: " + ", ".join(missing),
                            }
                        )
                        if failure_streak >= 3:
                            self.log.warning(
                                json.dumps(
                                    {
                                        "event": "circuit_breaker",
                                        "conversation_id": conversation_id,
                                        "turn": turn,
                                        "safe_mode": self.safe_mode,
                                    }
                                )
                            )
                            return "tool failures exceeded"
                        continue
                    props = schema.get("properties", {})
                    invalid: List[str] = []
                    for key, spec in props.items():
                        if key in args and isinstance(spec, dict) and "type" in spec:
                            expected = spec["type"]
                            val = args[key]
                            if expected == "string" and not isinstance(val, str):
                                invalid.append(key)
                            elif expected == "integer" and not isinstance(val, int):
                                invalid.append(key)
                            elif expected == "object" and not isinstance(val, dict):
                                invalid.append(key)
                    if invalid:
                        failure_streak += 1
                        self.log.warning(
                            json.dumps(
                                {
                                    "event": "invalid_tool_args",
                                    "name": name,
                                    "invalid_type": invalid,
                                    "conversation_id": conversation_id,
                                    "turn": turn,
                                    "request_id": request_id,
                                    "tool_call_id": tool_call_id,
                                    "safe_mode": self.safe_mode,
                                }
                            )
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "name": name,
                                "tool_call_id": tool_call_id,
                                "content": "invalid type for: " + ", ".join(invalid),
                            }
                        )
                        if failure_streak >= 3:
                            self.log.warning(
                                json.dumps(
                                    {
                                        "event": "circuit_breaker",
                                        "conversation_id": conversation_id,
                                        "turn": turn,
                                        "safe_mode": self.safe_mode,
                                    }
                                )
                            )
                            return "tool failures exceeded"
                        continue
                start = self.clock()
                envelope = dispatch(tc, request_id=request_id, safe_mode=self.safe_mode)
                raw = json.dumps(envelope, ensure_ascii=False)
                payload = _truncate(raw)
                elapsed_ms = int((self.clock() - start) * 1000)
                self.log.info(
                    json.dumps(
                        {
                            "event": "toolcall",
                            "name": name,
                            "elapsed_ms": elapsed_ms,
                            "size_before": len(raw),
                            "size_after": len(payload),
                            "conversation_id": conversation_id,
                            "turn": turn,
                            "request_id": request_id,
                            "tool_call_id": tool_call_id,
                            "safe_mode": self.safe_mode,
                        }
                    )
                )
                messages.append(
                    {
                        "role": "tool",
                        "name": name,
                        "tool_call_id": tool_call_id,
                        "content": payload,
                    }
                )
                tool_calls_used += 1
                if envelope.get("kind") != "ok":
                    failure_streak += 1
                else:
                    failure_streak = 0
                if failure_streak >= 3:
                    self.log.warning(
                        json.dumps(
                            {
                                "event": "circuit_breaker",
                                "conversation_id": conversation_id,
                                "turn": turn,
                                "safe_mode": self.safe_mode,
                            }
                        )
                    )
                    return "tool failures exceeded"
                messages = _shrink(messages)

        turn += 1
        start_call = self.clock()
        res = self.llm(_shrink(messages))
        if isinstance(res, tuple):
            final, usage = res
        else:
            final, usage = res, None
        elapsed = self.clock() - start_call
        if usage and isinstance(usage.get("completion_tokens"), int):
            tokens = usage.get("completion_tokens", 0)
            tps = tokens / elapsed if elapsed > 0 else float("inf")
            metrics.record_gauge("tokens_per_sec", tps)
            self.log.info(
                json.dumps(
                    {
                        "event": "llm_call",
                        "elapsed_ms": int(elapsed * 1000),
                        "tokens": tokens,
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "tokens_per_sec": tps,
                        "conversation_id": conversation_id,
                        "turn": turn,
                        "safe_mode": self.safe_mode,
                        "final": True,
                    }
                )
            )
        else:
            approx_tokens = len(final.split())
            tps = approx_tokens / elapsed if elapsed > 0 else float("inf")
            metrics.record_gauge("tokens_per_sec", tps)
            self.log.info(
                json.dumps(
                    {
                        "event": "llm_call",
                        "elapsed_ms": int(elapsed * 1000),
                        "approx_tokens": approx_tokens,
                        "approx_tokens_per_sec": tps,
                        "conversation_id": conversation_id,
                        "turn": turn,
                        "safe_mode": self.safe_mode,
                        "final": True,
                    }
                )
            )
        text, _ = _parse_toolcalls(final)
        return text.strip()


__all__ = [
    "Agent",
    "_parse_toolcalls",
    "_truncate",
    "MAX_TOOL_RESULT_CHARS",
    "MAX_TOOL_RESULT_TOKENS",
]
