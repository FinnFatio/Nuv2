from __future__ import annotations

# setx LLM_MODEL "D:\\modelos\\llama31-8b-instruct\\llama31-8b.Q4_K_M.gguf"
# setx N_CTX "8192"
# setx N_GPU_LAYERS "999"
# setx N_THREADS "8"

# --- ensure repo root on sys.path ---
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# ------------------------------------

import os  # noqa: E402
from typing import Any, Dict, List  # noqa: E402

import requests  # type: ignore[import-untyped]  # noqa: E402

from agent_local import Agent, _parse_toolcalls  # noqa: E402


STOP = ["</toolcall>", "</s>"]
_local_llm = None
_logged = False


PRE = (
    "Você é a Nu. Se o pedido exigir ferramenta, responda APENAS com "
    '<toolcall>{"name":"...","args":{...}}</toolcall>. '
    "Ferramentas (read-only, LLM-0): system.capture_screen(); system.ocr(path); "
    "system.info(); fs.list(path?); fs.read(path); web.read(url). "
    "Quando decidir usar ferramenta, responda APENAS com "
    '<toolcall>{"name":"...","args":{...}}</toolcall> '
    "(nunca texto junto); para URLs use sempre web.read(url); para listar arquivos, "
    "sempre fs.list(path?). Depois que eu te enviar o resultado da tool, você "
    "poderá responder ao usuário."
)


_FEW_SHOT = [
    {"role": "user", "content": "Tire um screenshot."},
    {
        "role": "assistant",
        "content": '<toolcall>{"name":"system.capture_screen","args":{}}</toolcall>',
    },
    {"role": "user", "content": "Resumo de https://ex.com"},
    {
        "role": "assistant",
        "content": '<toolcall>{"name":"web.read","args":{"url":"https://ex.com"}}</toolcall>',
    },
]


def _with_examples(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not any(m.get("role") in {"user", "system"} for m in msgs[:-1]):
        return _FEW_SHOT + list(msgs)
    return list(msgs)


def _with_preamble(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = list(msgs)
    idx_last_sys = max(
        (i for i, m in enumerate(out) if m.get("role") == "system"),
        default=-1,
    )
    if idx_last_sys >= 0 and str(out[idx_last_sys].get("content", "")).startswith(
        "[remaining_tools="
    ):
        out[idx_last_sys] = {
            "role": "system",
            "content": PRE + " " + out[idx_last_sys]["content"],
        }
    else:
        out = [{"role": "system", "content": PRE}] + out
    return out


def llamacpp_chat(
    messages: List[Dict[str, Any]],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Dict[str, Any]:
    """Minimal wrapper for llama.cpp compatible endpoints."""
    global _local_llm, _logged
    messages = _with_examples(messages)
    messages = _with_preamble(messages)
    endpoint = os.getenv("LLM_ENDPOINT")
    model = os.getenv("LLM_MODEL", "llama")
    if temperature is None:
        temperature = 0.2
    if endpoint:
        if not _logged:
            print(f"[llm] endpoint={endpoint} model={model}")
            _logged = True
        payload: Dict[str, Any] = {"model": model, "messages": messages, "stop": STOP}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        try:
            resp = requests.post(endpoint, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = str(data["choices"][0]["message"]["content"])
            text, toolcalls = _parse_toolcalls(content)
            usage = data.get("usage", {})
            return {"text": text, "toolcalls": toolcalls, "usage": usage}
        except requests.ConnectionError:
            print("[llm] endpoint indisponível → usando fallback local llama_cpp")

    if _local_llm is None:
        try:
            from llama_cpp import Llama
        except Exception as e:  # pragma: no cover - missing dep
            raise RuntimeError(
                "llama_cpp não disponível; instale ou defina LLM_ENDPOINT",
            ) from e
        N_CTX = int(os.getenv("N_CTX", "8192"))
        N_THREADS = int(os.getenv("N_THREADS", "6"))
        N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "999"))
        print(
            f"[llm] local model={model} n_ctx={N_CTX} n_gpu_layers={N_GPU_LAYERS} n_threads={N_THREADS}"
        )
        _local_llm = Llama(
            model_path=model,
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_gpu_layers=N_GPU_LAYERS,
            verbose=False,
        )
    result = _local_llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=STOP,
    )
    content = str(result["choices"][0]["message"]["content"])
    text, toolcalls = _parse_toolcalls(content)
    usage = result.get("usage", {})
    return {"text": text, "toolcalls": toolcalls, "usage": usage}


MODE = "observer"


def main() -> None:
    agent = Agent(llm=llamacpp_chat, safe_mode=True)  # type: ignore[arg-type]
    global MODE
    try:
        while True:
            prompt = input(">> ")
            if not prompt.strip():
                continue
            if prompt.startswith("/mode"):
                parts = prompt.split()
                if len(parts) == 2 and parts[1] in {"observer", "confirm"}:
                    MODE = parts[1]
                    print(f"mode set to {MODE}")
                else:
                    print("usage: /mode observer|confirm")
                continue
            if prompt.startswith("/stop"):
                print(STOP)
                continue
            reply = agent.chat(prompt)
            print(reply)
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
