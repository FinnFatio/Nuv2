import agent_local
import json

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
            assert messages[-1]["role"] == "tool"
            assert "unavailable" in messages[-1]["content"]
            return "done"

    llm = LLM()
    agent = Agent(llm=llm)
    assert agent.chat("hi") == "done"


def test_agent_invalid_args(monkeypatch):
    def llm(messages, **kwargs):
        if len(messages) == 1:
            return '<toolcall>{"name":"echo","args":{}}</toolcall>'
        assert messages[-1]["role"] == "tool"
        assert "missing args" in messages[-1]["content"]
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
        lambda name: {"name": name, "schema": {"required": ["msg"]}},
    )

    agent = Agent(llm=llm)
    assert agent.chat("hi") == "done"
    assert not called


def test_toolcall_log_includes_context(monkeypatch, capsys):
    def llm(messages, **kwargs):
        if len(messages) == 1:
            return '<toolcall>{"name":"echo"}</toolcall>'
        return "done"

    monkeypatch.setattr(agent_local, "dispatch", lambda req, request_id, safe_mode: {"kind": "ok"})
    monkeypatch.setattr(agent_local, "get_tool", lambda name: {"name": name})
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
    monkeypatch.setattr(agent_local, "get_tool", lambda name: {"name": name})

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
    assert entry["tokens"] == 3
    assert entry["tokens_per_sec"] == 3


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
    monkeypatch.setattr(agent_local, "get_tool", lambda name: {"name": name})
    monkeypatch.setattr(agent_local, "dispatch", lambda req, request_id, safe_mode: {"kind": "error"})
    agent = Agent(llm=LLM(), log=log)
    assert agent.chat("hi") == "tool failures exceeded"
    assert any(l.get("event") == "circuit_breaker" for l in log.logs)
