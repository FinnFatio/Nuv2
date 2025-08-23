import agent_local
import json
import uuid
import hashlib

import logger
from typing import Any, List, Dict

from agent_local import (
    Agent,
    _parse_toolcalls,
    _truncate,
    MAX_TOOL_RESULT_CHARS,
    MAX_TOOL_RESULT_TOKENS,
)


def test_parse_toolcalls_multiple_and_spaces():
    text = "Hello<toolcall>{\n \"name\": \"foo\", \"args\": {}}\n</toolcall>world<toolcall>{\"name\":\"bar\"}</toolcall>!"
    cleaned, tcs = _parse_toolcalls(text)
    assert cleaned == "Helloworld!"
    assert [tc["name"] for tc in tcs] == ["foo", "bar"]


def test_parse_toolcalls_tolerant_json():
    text = "<toolcall>{'name': 'baz', 'args': {'a': 1,}}</toolcall>"
    _, tcs = _parse_toolcalls(text)
    assert tcs[0]["name"] == "baz"
    assert tcs[0]["args"] == {"a": 1}


def test_parse_toolcalls_interleaved_with_text_newlines():
    text = (
        "one <toolcall>{\"name\":\"foo\"}</toolcall> two\n"
        "<toolcall>{\"name\":\"bar\"}</toolcall> three"
    )
    cleaned, tcs = _parse_toolcalls(text)
    assert cleaned == "one  two\n three"
    assert [tc["name"] for tc in tcs] == ["foo", "bar"]


def test_parse_toolcalls_trailing_comma_top_level():
    text = "<toolcall>{'name': 'qux',}</toolcall>"
    _, tcs = _parse_toolcalls(text)
    assert tcs[0]["name"] == "qux"


def test_parse_toolcalls_with_id():
    text = '<toolcall>{"name":"foo","id":"123","args":{}}</toolcall>'
    _, tcs = _parse_toolcalls(text)
    assert tcs[0]["id"] == "123"


def test_parse_toolcalls_alt_format():
    content = json.dumps(
        {
            "tool_calls": [
                {
                    "id": "x1",
                    "function": {"name": "foo", "arguments": json.dumps({"a": 1})},
                }
            ]
        }
    )
    text, tcs = _parse_toolcalls(content)
    assert text == ""
    assert tcs[0]["name"] == "foo"
    assert tcs[0]["args"] == {"a": 1}
    assert tcs[0]["id"] == "x1"


def test_truncate_payload():
    payload = "x" * (MAX_TOOL_RESULT_CHARS + 10)
    out = _truncate(payload)
    assert out.startswith("x" * MAX_TOOL_RESULT_CHARS)
    assert out.endswith("[truncated 10 chars]")


def test_truncate_payload_tokens():
    payload = "x " * (MAX_TOOL_RESULT_TOKENS + 5)
    out = _truncate(payload, char_limit=10000)
    prefix = " ".join(["x"] * MAX_TOOL_RESULT_TOKENS)
    assert out.startswith(prefix)
    assert out.strip().endswith("[truncated 5 tokens]")


def test_agent_no_toolcall_returns_text():
    def llm(messages, **kwargs):
        return "pong"

    agent = Agent(llm=llm)
    assert agent.chat("ping") == "pong"


def test_agent_unknown_tool_feedback():
    class LLM:
        def __init__(self):
            self.calls = 0
        def __call__(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return '<toolcall>{"name":"missing"}</toolcall>'
            assert messages[-2]["role"] == "tool"
            content = json.loads(messages[-2]["content"])
            assert messages[-1]["role"] == "system"
            assert messages[-1]["content"].startswith("[remaining_tools=")
            assert content["kind"] == "error"
            assert content["code"] == "unknown_tool"
            return "done"

    llm = LLM()
    agent = Agent(llm=llm)
    assert agent.chat("hi") == "done"


def test_remaining_tools_telemetry(monkeypatch):
    class LLM:
        def __init__(self):
            self.calls = 0
            self.messages: List[List[Dict[str, Any]]] = []

        def __call__(self, messages, **kwargs):
            self.calls += 1
            self.messages.append([m.copy() for m in messages])
            if self.calls == 1:
                return '<toolcall>{"name":"echo"}</toolcall>'
            return "done"

    monkeypatch.setattr(
        agent_local, "dispatch", lambda req, request_id, safe_mode: {"kind": "ok"}
    )
    monkeypatch.setattr(
        agent_local, "get_tool", lambda name: {"name": name, "enabled_in_safe_mode": True}
    )
    llm = LLM()
    agent = Agent(llm=llm)
    assert agent.chat("hi") == "done"
    assert llm.messages[0][-1]["content"] == "[remaining_tools=3]"
    assert llm.messages[1][-1]["content"] == "[remaining_tools=2]"


def test_agent_invalid_args(monkeypatch):
    def llm(messages, **kwargs):
        if len(messages) == 2:
            return '<toolcall>{"name":"echo","args":{}}</toolcall>'
        assert messages[-2]["role"] == "tool"
        content = json.loads(messages[-2]["content"])
        assert messages[-1]["role"] == "system"
        assert messages[-1]["content"].startswith("[remaining_tools=")
        assert content["kind"] == "error"
        assert content["code"] == "missing_args"
        return "done"

    called = False

    def fake_dispatch(req, request_id, safe_mode):
        nonlocal called
        called = True
        return {"kind": "ok"}

    monkeypatch.setattr(agent_local, "dispatch", fake_dispatch)
    monkeypatch.setattr(
        agent_local,
        "get_tool",
        lambda name: {"name": name, "enabled_in_safe_mode": True, "schema": {"required": ["msg"]}},
    )

    agent = Agent(llm=llm)
    assert agent.chat("hi") == "done"
    assert not called


def test_toolcall_log_includes_context(monkeypatch, capsys):
    def llm(messages, **kwargs):
        if len(messages) == 2:
            return '<toolcall>{"name":"echo"}</toolcall>'
        return "done"

    monkeypatch.setattr(agent_local, "dispatch", lambda req, request_id, safe_mode: {"kind": "ok"})
    monkeypatch.setattr(
        agent_local, "get_tool", lambda name: {"name": name, "enabled_in_safe_mode": True}
    )
    logger.setup(enable=True, jsonl=True)
    agent = Agent(llm=llm)
    agent.chat("hi")
    logs = [json.loads(line) for line in capsys.readouterr().err.strip().splitlines()]
    tool_log = next(l for l in logs if l.get("event") == "toolcall")
    assert tool_log["conversation_id"]
    assert tool_log["turn"] == 1
    assert tool_log["request_id"]
    assert tool_log["tool_call_id"]
    assert "safe_mode" in tool_log


def test_agent_respects_tool_limit(monkeypatch):
    class LLM:
        def __init__(self):
            self.calls = 0
        def __call__(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return "".join(
                    "<toolcall>{\"name\":\"echo\"}</toolcall>" for _ in range(5)
                )
            return "done"

    llm = LLM()
    count = 0

    def fake_dispatch(req, request_id, safe_mode):
        nonlocal count
        count += 1
        return {"kind": "ok", "result": "ok"}

    monkeypatch.setattr(agent_local, "dispatch", fake_dispatch)
    monkeypatch.setattr(
        agent_local, "get_tool", lambda name: {"name": name, "enabled_in_safe_mode": True}
    )

    agent = Agent(llm=llm, max_tools=3)
    assert agent.chat("hi") == "done"
    assert count == 3


def test_llm_tokens_per_second_logged(monkeypatch):
    class FakeClock:
        def __init__(self):
            self.t = 0.0
        def __call__(self):
            v = self.t
            self.t += 1.0
            return v

    class DummyLogger:
        def __init__(self):
            self.logs: List[Dict[str, Any]] = []
        def info(self, msg: str) -> None:
            self.logs.append(json.loads(msg))
        def warning(self, msg: str) -> None:
            self.logs.append(json.loads(msg))

    clock = FakeClock()
    log = DummyLogger()

    def llm(messages, **kwargs):
        return "a b c"

    agent = Agent(llm=llm, log=log, clock=clock)
    assert agent.chat("hi") == "a b c"
    entry = next(l for l in log.logs if l.get("event") == "llm_call" and not l.get("final"))
    assert entry["approx_tokens"] == 3
    assert entry["approx_tokens_per_sec"] == 3


def test_circuit_breaker_on_failures(monkeypatch):
    class LLM:
        def __init__(self):
            self.calls = 0
        def __call__(self, messages, **kwargs):
            self.calls += 1
            return '<toolcall>{"name":"echo"}</toolcall>'

    class DummyLogger:
        def __init__(self):
            self.logs: List[Dict[str, Any]] = []
        def info(self, msg: str) -> None:
            self.logs.append(json.loads(msg))
        def warning(self, msg: str) -> None:
            self.logs.append(json.loads(msg))

    log = DummyLogger()
    monkeypatch.setattr(
        agent_local, "get_tool", lambda name: {"name": name, "enabled_in_safe_mode": True}
    )
    monkeypatch.setattr(agent_local, "dispatch", lambda req, request_id, safe_mode: {"kind": "error"})
    agent = Agent(llm=LLM(), log=log)
    assert (
        agent.chat("hi")
        == "Falhei repetidamente ao usar ferramentas nesta tarefa. Posso tentar outro caminho (sem tools) ou você quer ajustar o pedido?"
    )
    assert any(l.get("event") == "circuit_breaker" for l in log.logs)


def test_llm_headers_api_key(monkeypatch):
    captured: list[dict[str, str] | None] = []

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.append(headers)
        class Resp:
            def raise_for_status(self):
                pass
            def json(self):
                return {"choices": [{"message": {"content": "hi"}}]}
        return Resp()

    monkeypatch.setenv("LLM_ENDPOINT", "http://llm")
    monkeypatch.setenv("LLM_MODEL", "gpt")
    monkeypatch.setenv("LLM_API_KEY", "abc")
    monkeypatch.delenv("LLM_AUTH_HEADER", raising=False)
    monkeypatch.setattr(agent_local.requests, "post", fake_post)
    chat = agent_local._default_llm_backend()
    assert chat([{ "role": "user", "content": "hi" }]) == "hi"
    assert captured[0]["Authorization"] == "Bearer abc"


def test_llm_headers_custom_header(monkeypatch):
    captured: list[dict[str, str] | None] = []

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.append(headers)
        class Resp:
            def raise_for_status(self):
                pass
            def json(self):
                return {"choices": [{"message": {"content": "hi"}}]}
        return Resp()

    monkeypatch.setenv("LLM_ENDPOINT", "http://llm")
    monkeypatch.setenv("LLM_MODEL", "gpt")
    monkeypatch.setenv("LLM_AUTH_HEADER", "X-Test: 123")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(agent_local.requests, "post", fake_post)
    chat = agent_local._default_llm_backend()
    assert chat([{ "role": "user", "content": "hi" }]) == "hi"
    assert captured[0]["X-Test"] == "123"


def test_tool_retry_policy(monkeypatch):
    class LLM:
        def __init__(self):
            self.calls = 0
        def __call__(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return '<toolcall>{"name":"echo","id":"1"}</toolcall>'
            assert messages[-2]["role"] == "tool"
            assert messages[-1]["role"] == "system"
            assert messages[-1]["content"].startswith("[remaining_tools=")
            return "done"

    attempts = []

    def fake_dispatch(req, request_id, safe_mode):
        attempts.append(None)
        if len(attempts) == 1:
            return {"kind": "error"}
        return {"kind": "ok"}

    monkeypatch.setattr(agent_local, "dispatch", fake_dispatch)
    monkeypatch.setattr(
        agent_local,
        "get_tool",
        lambda name: {"name": name, "enabled_in_safe_mode": True, "schema": {"x-retry": 1}},
    )
    monkeypatch.setattr(agent_local.time, "sleep", lambda s: None)
    agent = Agent(llm=LLM())
    assert agent.chat("hi") == "done"
    assert len(attempts) == 2


def test_safe_mode_blocks_destructive(monkeypatch):
    class LLM:
        def __init__(self):
            self.calls = 0
        def __call__(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return '<toolcall>{"name":"boom"}</toolcall>'
            assert messages[-2]["role"] == "tool"
            content = json.loads(messages[-2]["content"])
            assert messages[-1]["role"] == "system"
            assert messages[-1]["content"].startswith("[remaining_tools=")
            assert content["code"] == "forbidden_in_safe_mode"
            assert (
                content["hint"] == "peça confirmação ou proponha alternativa"
            )
            return "done"

    called = False

    def fake_dispatch(req, request_id, safe_mode):
        nonlocal called
        called = True
        return {"kind": "ok"}

    monkeypatch.setattr(agent_local, "dispatch", fake_dispatch)
    monkeypatch.setattr(
        agent_local,
        "get_tool",
        lambda name: {"name": name, "enabled_in_safe_mode": True, "safety": "destructive"},
    )
    agent = Agent(llm=LLM())
    assert agent.chat("hi") == "done"
    assert called is False


def test_agent_range_validation(monkeypatch):
    def llm(messages, **kwargs):
        if len(messages) == 2:
            return '<toolcall>{"name":"echo","args":{"num":5}}</toolcall>'
        assert messages[-2]["role"] == "tool"
        content = json.loads(messages[-2]["content"])
        assert messages[-1]["role"] == "system"
        assert messages[-1]["content"].startswith("[remaining_tools=")
        assert content["code"] == "invalid_type"
        return "ok"

    called = False

    def fake_dispatch(req, request_id, safe_mode):
        nonlocal called
        called = True
        return {"kind": "ok"}

    monkeypatch.setattr(agent_local, "dispatch", fake_dispatch)
    monkeypatch.setattr(
        agent_local,
        "get_tool",
        lambda name: {
            "name": name,
            "enabled_in_safe_mode": True,
            "schema": {
                "required": ["num"],
                "properties": {"num": {"type": "integer", "minimum": 10}},
            },
        },
    )

    agent = Agent(llm=llm)
    assert agent.chat("hi") == "ok"
    assert called is False


def test_tool_limit_reached_logs_hash(monkeypatch):
    class LLM:
        def __init__(self):
            self.calls = 0

        def __call__(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return (
                    '<toolcall>{"name":"echo","args":{}}</toolcall>'
                    '<toolcall>{"name":"echo","args":{}}</toolcall>'
                )
            return "done"

    class DummyLogger:
        def __init__(self):
            self.logs: List[Dict[str, Any]] = []

        def info(self, msg: str) -> None:
            self.logs.append(json.loads(msg))

        def warning(self, msg: str) -> None:
            self.logs.append(json.loads(msg))

    log = DummyLogger()
    monkeypatch.setattr(agent_local, "dispatch", lambda req, request_id, safe_mode: {"kind": "ok"})
    monkeypatch.setattr(
        agent_local, "get_tool", lambda name: {"name": name, "enabled_in_safe_mode": True}
    )

    agent = Agent(llm=LLM(), max_tools=1, log=log)
    assert agent.chat("hi") == "done"
    evt = next(l for l in log.logs if l.get("event") == "tool_limit_reached")
    expected = uuid.uuid5(
        uuid.NAMESPACE_OID,
        '<toolcall>{"name":"echo","args":{}}</toolcall><toolcall>{"name":"echo","args":{}}</toolcall>',
    ).hex[:8]
    assert evt["reply_hash"] == expected


def test_tool_result_logs_hash_and_size(monkeypatch):
    class LLM:
        def __init__(self):
            self.calls = 0

        def __call__(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return '<toolcall>{"name":"echo"}</toolcall>'
            return "done"

    envelope = {"kind": "ok", "result": "hello"}
    raw = json.dumps(envelope, ensure_ascii=False)
    expected_hash = hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:12]

    monkeypatch.setattr(
        agent_local, "dispatch", lambda req, request_id, safe_mode: envelope
    )
    monkeypatch.setattr(
        agent_local, "get_tool", lambda name: {"name": name, "enabled_in_safe_mode": True}
    )

    class DummyLogger:
        def __init__(self):
            self.logs: List[Dict[str, Any]] = []

        def info(self, msg: str) -> None:
            self.logs.append(json.loads(msg))

        def warning(self, msg: str) -> None:
            self.logs.append(json.loads(msg))

    log = DummyLogger()
    agent = Agent(llm=LLM(), log=log)
    assert agent.chat("hi") == "done"
    evt = next(l for l in log.logs if l.get("hash"))
    assert evt["name"] == "echo"
    assert evt["hash"] == expected_hash
    assert evt["size"] == len(raw)


def test_tool_result_preview_respects_max(monkeypatch):
    class LLM:
        def __init__(self):
            self.calls = 0

        def __call__(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return '<toolcall>{"name":"echo"}</toolcall>'
            return "done"

    envelope = {"kind": "ok", "result": "x" * 50}
    monkeypatch.setattr(
        agent_local, "dispatch", lambda req, request_id, safe_mode: envelope
    )
    monkeypatch.setattr(
        agent_local, "get_tool", lambda name: {"name": name, "enabled_in_safe_mode": True}
    )

    class DummyLogger:
        def __init__(self):
            self.logs: List[Dict[str, Any]] = []

        def info(self, msg: str) -> None:
            self.logs.append(json.loads(msg))

        def warning(self, msg: str) -> None:
            self.logs.append(json.loads(msg))

    log = DummyLogger()
    monkeypatch.setattr(agent_local.settings, "MAX_LOG_CHARS", 10)
    agent = Agent(llm=LLM(), log=log)
    assert agent.chat("hi") == "done"
    raw = json.dumps(envelope, ensure_ascii=False)
    evt = next(l for l in log.logs if l.get("preview") is not None)
    assert evt["preview"] == raw[:10]


def test_whitespace_normalized_in_reply():
    def llm(messages, **kwargs):
        return "line1   \nline2\n"

    agent = Agent(llm=llm, max_tools=0)
    assert agent.chat("hi") == "line1\nline2"


def test_tool_reply_whitespace_normalized(monkeypatch):
    class LLM:
        def __init__(self):
            self.calls = 0

        def __call__(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return '<toolcall>{"name":"echo"}</toolcall>'
            content = messages[-2]["content"]
            assert "foo   bar" not in content
            assert "foo  bar" in content
            return "done"

    envelope = {"kind": "ok", "result": "foo   bar"}
    monkeypatch.setattr(
        agent_local, "dispatch", lambda req, request_id, safe_mode: envelope
    )
    monkeypatch.setattr(
        agent_local, "get_tool", lambda name: {"name": name, "enabled_in_safe_mode": True}
    )
    agent = Agent(llm=LLM())
    assert agent.chat("hi") == "done"


def test_dry_run_skips_dispatch(monkeypatch):
    class LLM:
        def __init__(self):
            self.calls = 0

        def __call__(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return '<toolcall>{"name":"echo","args":{"msg":"hi"}}</toolcall>'
            assert messages[-2]["role"] == "tool"
            content = json.loads(messages[-2]["content"])
            assert messages[-1]["role"] == "system"
            assert messages[-1]["content"].startswith("[remaining_tools=")
            assert content["dry_run"] is True
            assert content["args"] == {"msg": "hi"}
            return "done"

    called = False

    def fake_dispatch(req, request_id, safe_mode):
        nonlocal called
        called = True
        return {"kind": "ok"}

    monkeypatch.setattr(agent_local, "dispatch", fake_dispatch)
    monkeypatch.setattr(
        agent_local, "get_tool", lambda name: {"name": name, "enabled_in_safe_mode": True}
    )
    agent = Agent(llm=LLM())
    agent.dry_run = True
    assert agent.chat("hi") == "done"
    assert called is False
