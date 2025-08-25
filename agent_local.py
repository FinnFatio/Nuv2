from __future__ import annotations

import json
import os
import re
import ast
import uuid
import time
import random
import logging
import hashlib
from typing import Any, Dict, List, Tuple, TypedDict, Protocol, Callable

import requests  # type: ignore[import-untyped]
from typing import cast

from dispatcher import dispatch
from registry import get_tool, violates_policy
import settings
import logger as _logger
import metrics
from tools import register_all_tools as _register_all_tools

_TOOLS_READY = False


def _ensure_tools() -> None:
    global _TOOLS_READY
    if not _TOOLS_READY:
        _register_all_tools()
        _TOOLS_READY = True


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
    ) -> str: ...


_TOOLCALL_RE = re.compile(r"<toolcall>(.*?)</toolcall>", re.DOTALL)

_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_RE_USERPATH = re.compile(r"C:\\Users\\[^\\]+", re.IGNORECASE)
_RE_TOKEN = re.compile(
    r"(?:api[_-]?key|token|secret)\s*[:=]\s*([A-Za-z0-9._-]{8,})", re.IGNORECASE
)


def _redact(text: str) -> str:
    t = _RE_EMAIL.sub("[REDACTED_EMAIL]", text)
    t = _RE_USERPATH.sub(lambda _: "C:\\Users\\<redacted>", t)
    t = _RE_TOKEN.sub(lambda m: m.group(0).replace(m.group(1), "<redacted>"), t)
    return t


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
        return (
            text[:char_limit] + "..." + f" [truncated {len(text) - char_limit} chars]"
        )
    return text


def _parse_toolcalls(content: str) -> Tuple[str, List[ToolCall]]:
    toolcalls: List[ToolCall] = []

    # Support JSON formats like {"tool_calls": [...]}
    try:
        data = json.loads(content)
    except Exception:
        data = None

    def _append(name: str, args: Any, tc_id: str) -> bool:
        name = str(name).strip().lower()
        if not re.fullmatch(r"[a-z0-9._-]{1,64}", name):
            return False
        if not isinstance(args, dict):
            args = {}
        else:
            try:
                if len(json.dumps(args)) > 2000:
                    args = {}
            except Exception:
                args = {}
        toolcalls.append({"name": name, "args": args, "id": tc_id})
        return True

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
                    name = func.get("name", "")
                    args_raw = func.get("arguments", {})
                    try:
                        args = (
                            json.loads(args_raw)
                            if isinstance(args_raw, str)
                            else args_raw
                        )
                    except Exception:
                        args = {}
                    _append(name, args, str(item.get("id", "")))
                else:
                    _append(
                        item.get("name", ""),
                        item.get("args", {}),
                        str(item.get("id", "")),
                    )
            return str(data.get("content", "")).strip(), toolcalls

    def _handle_json(inner: str) -> bool:
        data: Dict[str, Any] | None = None
        try:
            data = json.loads(inner)
        except Exception:
            try:
                data = ast.literal_eval(inner)
            except Exception:
                return False
        if isinstance(data, dict):
            return _append(
                data.get("name", ""),
                data.get("args", {}),
                str(data.get("id", "")),
            )
        return False

    def repl(match: re.Match[str]) -> str:
        return "" if _handle_json(match.group(1)) else match.group(0)

    cleaned = _TOOLCALL_RE.sub(repl, content)

    if "<toolcall>" in cleaned:
        if cleaned.count("<toolcall>") == 1:
            start = cleaned.find("<toolcall>")
            prefix = cleaned[:start]
            rest = cleaned[start + len("<toolcall>") :]
            brace = rest.find("{")
            if brace != -1:
                depth = 0
                in_str = False
                esc = False
                pos = brace
                while pos < len(rest):
                    ch = rest[pos]
                    if in_str:
                        if ch == '"' and not esc:
                            in_str = False
                        esc = ch == "\\" and not esc
                    else:
                        if ch == '"':
                            in_str = True
                        elif ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                pos += 1
                                break
                    pos += 1
                if depth == 0:
                    inner = rest[brace:pos]
                    if _handle_json(inner):
                        cleaned = prefix + rest[pos:]
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
                headers: Dict[str, str] = {}
                api_key = os.getenv("LLM_API_KEY", "").strip()
                auth_hdr = os.getenv("LLM_AUTH_HEADER", "").strip()
                if api_key and not auth_hdr:
                    headers["Authorization"] = f"Bearer {api_key}"
                elif auth_hdr:
                    k, v = auth_hdr.split(":", 1)
                    headers[k.strip()] = v.strip()
                resp = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers or None,
                    timeout=timeout,
                )
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
        temperature: float = 0.2,
        max_tokens: int = 256,
    ) -> None:
        self.llm: LLMFn = llm or _default_llm_backend(endpoint=endpoint, model=model)
        self.max_tools = max_tools
        self.safe_mode = settings.SAFE_MODE if safe_mode is None else safe_mode
        self.log = log or _logger.get_logger()
        self.clock = clock or time.time
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model = model or os.getenv("LLM_MODEL", "")

    def chat(self, prompt: str) -> str:
        _ensure_tools()
        start_turn = self.clock()
        messages: Messages = [{"role": "user", "content": prompt}]
        tool_calls_used = 0
        conversation_id = str(uuid.uuid4())
        turn = 0
        failure_streak = 0

        last_tool = ""
        while tool_calls_used < self.max_tools:
            turn += 1
            messages = _shrink(messages, max_msgs=20)
            remaining = self.max_tools - tool_calls_used
            messages.append(
                {"role": "system", "content": f"[remaining_tools={remaining}]"}
            )
            start_call = self.clock()
            res = self.llm(
                messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            if isinstance(res, dict):
                raw = str(res.get("text", ""))
                toolcalls = list(res.get("toolcalls", []))
                usage = res.get("usage")
                text = raw
            else:
                if isinstance(res, tuple):
                    raw, usage = res
                else:
                    raw, usage = res, None
                raw = str(raw)
                text, toolcalls = _parse_toolcalls(raw)
            elapsed = self.clock() - start_call
            if usage and isinstance(usage.get("completion_tokens"), int):
                tokens = usage.get("completion_tokens", 0)
                tps = tokens / elapsed if elapsed > 0 else float("inf")
                metrics.record_gauge("tokens_per_sec", tps, label=self.model)
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
                approx_tokens = len(raw.split())
                tps = approx_tokens / elapsed if elapsed > 0 else float("inf")
                metrics.record_gauge("tokens_per_sec", tps, label=self.model)
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
            remaining = self.max_tools - tool_calls_used
            if len(toolcalls) > remaining:
                h = uuid.uuid5(uuid.NAMESPACE_OID, raw).hex[:8]
                self.log.info(
                    json.dumps(
                        {
                            "event": "tool_limit_reached",
                            "limit": self.max_tools,
                            "reply_hash": h,
                            "conversation_id": conversation_id,
                            "turn": turn,
                            "request_id": None,
                            "tool_call_id": None,
                            "safe_mode": self.safe_mode,
                        }
                    )
                )
            toolcalls = toolcalls[:remaining]
            messages.append({"role": "assistant", "content": text})
            if not toolcalls:
                match = re.fullmatch(
                    r"\s*([a-z0-9._-]{1,64})\s*\((.*)\)\s*", text, re.I
                )
                if match:
                    name = match.group(1).lower()
                    arg_str = match.group(2)
                    if not arg_str.strip():
                        args = {}
                    else:
                        arg_str = arg_str.strip()
                        if arg_str.startswith("{"):
                            try:
                                args = json.loads(arg_str)
                            except Exception:
                                try:
                                    args = ast.literal_eval("{" + arg_str + "}")
                                except Exception:
                                    args = {}
                        else:
                            try:
                                args = ast.literal_eval("{" + arg_str + "}")
                            except Exception:
                                args = {}
                        if not isinstance(args, dict):
                            args = {}
                        else:
                            try:
                                if len(json.dumps(args)) > 2000:
                                    args = {}
                            except Exception:
                                args = {}
                    toolcalls = [{"name": name, "args": args, "id": str(uuid.uuid4())}]
                else:
                    failure_streak = 0
                    elapsed_turn = int((self.clock() - start_turn) * 1000)
                    metrics.record_agent_turn(elapsed_turn)
                    return re.sub(r"\s+\n", "\n", text.strip())
            for tc in toolcalls:
                raw = tc.get("name", "")
                name = raw.strip().lower()
                if not re.fullmatch(r"[a-z0-9._-]{1,64}", name):
                    self.log.warning(
                        json.dumps({"event": "tool_name_invalid", "raw": raw})
                    )
                    continue
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
                            "content": json.dumps(
                                {
                                    "kind": "error",
                                    "code": "unknown_tool",
                                    "note": f"tool {name} unavailable",
                                    "retry_safe": False,
                                }
                            ),
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
                        elapsed_turn = int((self.clock() - start_turn) * 1000)
                        metrics.record_agent_turn(elapsed_turn)
                        return (
                            "Falhei repetidamente ao usar ferramentas nesta tarefa. "
                            "Posso tentar outro caminho (sem tools) ou você quer ajustar o pedido?"
                        )
                    continue
                if violates_policy(tool, self.safe_mode):
                    metrics.record_policy_block("destructive")
                    messages.append(
                        {
                            "role": "tool",
                            "name": name,
                            "tool_call_id": tool_call_id,
                            "content": json.dumps(
                                {
                                    "kind": "error",
                                    "code": "forbidden_in_safe_mode",
                                    "hint": "peça confirmação ou proponha alternativa",
                                }
                            ),
                        }
                    )
                    continue
                if self.safe_mode and not tool.get("enabled_in_safe_mode", False):
                    metrics.record_policy_block("safe_mode")
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
                            "content": json.dumps(
                                {
                                    "kind": "error",
                                    "code": "disabled_in_safe_mode",
                                    "note": f"tool {name} disabled in safe_mode",
                                    "retry_safe": False,
                                }
                            ),
                        }
                    )
                    continue
                args = tc.get("args", {})
                if not isinstance(args, dict):
                    args = {}
                else:
                    try:
                        if len(json.dumps(args)) > 2000:
                            args = {}
                    except Exception:
                        args = {}
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
                                "content": json.dumps(
                                    {
                                        "kind": "error",
                                        "code": "missing_args",
                                        "note": ", ".join(missing),
                                        "retry_safe": False,
                                    }
                                ),
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
                            elapsed_turn = int((self.clock() - start_turn) * 1000)
                            metrics.record_agent_turn(elapsed_turn)
                            return (
                                "Falhei repetidamente ao usar ferramentas nesta tarefa. "
                                "Posso tentar outro caminho (sem tools) ou você quer ajustar o pedido?"
                            )
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
                            minv = spec.get("minimum")
                            maxv = spec.get("maximum")
                            if isinstance(val, (int, float)):
                                if minv is not None and val < minv:
                                    invalid.append(key)
                                if maxv is not None and val > maxv:
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
                                "content": json.dumps(
                                    {
                                        "kind": "error",
                                        "code": "invalid_type",
                                        "note": ", ".join(invalid),
                                        "retry_safe": False,
                                    }
                                ),
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
                            elapsed_turn = int((self.clock() - start_turn) * 1000)
                            metrics.record_agent_turn(elapsed_turn)
                            return (
                                "Falhei repetidamente ao usar ferramentas nesta tarefa. "
                                "Posso tentar outro caminho (sem tools) ou você quer ajustar o pedido?"
                            )
                        continue
                if getattr(self, "dry_run", False):
                    messages.append(
                        {
                            "role": "tool",
                            "name": name,
                            "tool_call_id": tool_call_id,
                            "content": json.dumps(
                                {
                                    "kind": "ok",
                                    "dry_run": True,
                                    "args": args,
                                }
                            ),
                        }
                    )
                    tool_calls_used += 1
                    continue
                retry = int((schema or {}).get("x-retry", 0))
                attempts = 1 + max(0, retry)
                envelope: Dict[str, Any] = {}
                payload = ""
                metrics.record_agent_tool_name(name)
                for i in range(attempts):
                    start = self.clock()
                    envelope = dispatch(
                        tc, request_id=request_id, safe_mode=self.safe_mode
                    )
                    raw = json.dumps(envelope, ensure_ascii=False)
                    raw_hash = hashlib.sha256(
                        raw.encode("utf-8", "ignore")
                    ).hexdigest()[:12]
                    self.log.info(
                        json.dumps(
                            {
                                "event": "tool_result",
                                "name": name,
                                "hash": raw_hash,
                                "size": len(raw),
                            }
                        )
                    )
                    payload = _truncate(_redact(raw))
                    payload = re.sub(r"\s{3,}", "  ", payload)
                    short = payload[: settings.MAX_LOG_CHARS]
                    self.log.info(
                        json.dumps({"event": "tool_result", "preview": short})
                    )
                    elapsed_ms = int((self.clock() - start) * 1000)
                    outcome = envelope.get("kind", "error")
                    if outcome == "error":
                        outcome = envelope.get("code", "error")
                    metrics.record_agent_tool_use(name, outcome, elapsed_ms)
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
                                "attempt": i + 1,
                                "attempts": attempts,
                                "outcome": outcome,
                            }
                        )
                    )
                    if envelope.get("kind") != "error":
                        break
                    if i + 1 < attempts:
                        time.sleep(0.2 * (i + 1))

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
                    elapsed_turn = int((self.clock() - start_turn) * 1000)
                    metrics.record_agent_turn(elapsed_turn)
                    return (
                        "Falhei repetidamente ao usar ferramentas nesta tarefa. "
                        "Posso tentar outro caminho (sem tools) ou você quer ajustar o pedido?"
                    )
                messages = _shrink(messages, max_msgs=20)

        turn += 1
        messages = _shrink(messages, max_msgs=20)
        start_call = self.clock()
        res = self.llm(
            messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        if isinstance(res, dict):
            final = str(res.get("text", ""))
            usage = res.get("usage")
        else:
            if isinstance(res, tuple):
                final, usage = res
            else:
                final, usage = res, None
            final = str(final)
        elapsed = self.clock() - start_call
        if usage and isinstance(usage.get("completion_tokens"), int):
            tokens = usage.get("completion_tokens", 0)
            tps = tokens / elapsed if elapsed > 0 else float("inf")
            metrics.record_gauge("tokens_per_sec", tps, label=self.model)
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
            metrics.record_gauge("tokens_per_sec", tps, label=self.model)
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
        if not isinstance(res, dict):
            final, _ = _parse_toolcalls(final)
        text = final
        elapsed_turn = int((self.clock() - start_turn) * 1000)
        metrics.record_agent_turn(elapsed_turn)
        return re.sub(r"\s+\n", "\n", text.strip())


__all__ = [
    "Agent",
    "_parse_toolcalls",
    "_truncate",
    "MAX_TOOL_RESULT_CHARS",
    "MAX_TOOL_RESULT_TOKENS",
]
