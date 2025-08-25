from __future__ import annotations

# default temperature=0.2; N_CTX/N_GPU_LAYERS/N_THREADS via env (example using Windows setx)
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

import base64  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import importlib.util  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any, Dict, List  # noqa: E402

import requests  # type: ignore[import-untyped]  # noqa: E402

from agent_local import Agent, _parse_toolcalls  # noqa: E402
from tools import register_all_tools  # noqa: E402
from registry import REGISTRY  # noqa: E402

register_all_tools()
msg = f"[tools] {len(REGISTRY)} registered; optional deps: pip install -r requirements-optional.txt"
try:
    import metrics  # type: ignore

    total = metrics.summary().get("gauges", {}).get("agent_tool_name_total")
    if total is not None:
        msg += f" (agent_tool_name_total={total})"
except Exception:
    pass
print(msg)


STOP = ["</toolcall>", "</s>"]

SAMPLE_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y0bZ9wAAAAASUVORK5CYII="  # PNG 1x1


def ensure_sample_png(path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_bytes(base64.b64decode(SAMPLE_PNG_B64))


_logged = False
_fallback_logged = False


# substitua a função llamacpp_chat por esta versão com fallback local
_local_llm = None


PRE = (
    "Você é a Nu. Se o pedido exigir ferramenta, responda APENAS com "
    '<toolcall>{"name":"...","args":{...}}</toolcall>. '
    "Ferramentas (read-only, LLM-0): system.capture_screen(); system.ocr(...); "
    "system.info(); fs.list(...); fs.read(...); archive.list(...); archive.read(...); "
    "web.read(...); ui.what_under_mouse(). "
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
    {"role": "user", "content": "O que está sob o cursor?"},
    {
        "role": "assistant",
        "content": '<toolcall>{"name":"ui.what_under_mouse","args":{}}</toolcall>',
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
    """Chat wrapper com STOP e fallback p/ llama_cpp local quando não há endpoint."""
    global _local_llm, _logged, _fallback_logged
    messages = _with_examples(messages)
    messages = _with_preamble(messages)
    endpoint = os.getenv("LLM_ENDPOINT", "").strip() or None
    model = os.getenv("LLM_MODEL", "llama")
    disable_local = os.getenv("LLM_DISABLE_LOCAL_FALLBACK") == "1"
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

    if disable_local or importlib.util.find_spec("llama_cpp") is None:
        global _fallback_logged
        if not _fallback_logged:
            print(
                "[llm] fallback local desabilitado (LLM_DISABLE_LOCAL_FALLBACK=1 ou llama_cpp ausente)"
            )
            _fallback_logged = True
        raise RuntimeError(
            "LLM endpoint indisponível e fallback local desativado/ausente"
        )

    if _local_llm is None:
        from llama_cpp import Llama  # requer: pip install llama-cpp-python

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


def main() -> None:
    sample = "experiments/llm_sandbox/assets/sample.png"
    ensure_sample_png(sample)
    prompts = [
        ("Tire um screenshot da tela.", "ok"),
        ("Mostre a posição atual do cursor e faça um crop dessa área.", "error"),
        ("O que está sob o mouse agora?", "error"),
        (f"Rode OCR no arquivo {sample}.", "error"),
        ("Liste os arquivos do diretório atual.", "ok"),
        ("Leia https://example.com e resuma.", "ok"),
    ]
    agent = Agent(llm=llamacpp_chat, safe_mode=True)  # type: ignore[arg-type]
    results = []
    for p, expected in prompts:
        try:
            output = agent.chat(p)
        except RuntimeError as e:
            print(e)
            return
        lowered = output.lower()
        status = "error" if any(k in lowered for k in ("forbidden", "policy", "error")) else "ok"
        if expected == "error" and status == "ok":
            status = "unexpected_ok"
        elif expected == "ok" and status == "error":
            status = "unexpected_error"
        results.append({"prompt": p, "output": output, "status": status})
    out_path = Path("llm_eval_results.json")
    out_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
