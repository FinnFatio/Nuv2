from __future__ import annotations

import requests
import pytest

from experiments.llm_sandbox.nu_repl import llamacpp_chat


def test_fallback_disabled(monkeypatch):
    monkeypatch.setenv("LLM_ENDPOINT", "http://dummy")
    monkeypatch.setenv("LLM_DISABLE_LOCAL_FALLBACK", "1")

    def fake_post(*args, **kwargs):  # simulate endpoint down
        raise requests.ConnectionError

    monkeypatch.setattr("experiments.llm_sandbox.nu_repl.requests.post", fake_post)
    with pytest.raises(RuntimeError) as exc:
        llamacpp_chat([{"role": "user", "content": "hi"}])
    assert "LLM endpoint indisponível e fallback local desativado/ausente" in str(
        exc.value
    )
