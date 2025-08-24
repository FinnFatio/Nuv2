from __future__ import annotations

# Examples of expected configuration:
# setx LLM_MODEL "D:\\modelos\\llama31-8b-instruct\\llama31-8b.Q4_K_M.gguf"
# setx N_CTX "8192"
# setx N_GPU_LAYERS "999"
# setx N_THREADS "8"
# (no LLM_ENDPOINT in session to force local mode)

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests  # type: ignore[import-untyped]

from agent_local import Agent, _parse_toolcalls

SAMPLE_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y0bZ9wAAAAASUVORK5CYII="  # PNG 1x1


def ensure_sample_png(path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_bytes(base64.b64decode(SAMPLE_PNG_B64))


_local_llm = None
_logged = False


_PREAMBLE = (
    "Você é a Nu. Se o pedido exigir ferramenta, responda APENAS com "
    '<toolcall>{"name":"...","args":{...}}</toolcall>. '
    "Ferramentas disponíveis (read-only, LLM-0): system.capture_screen(); "
    "system.ocr(path); system.info(); fs.list(path?); fs.read(path); "
    "web.read(url). Depois que eu te enviar o resultado da tool, você "
    "poderá responder ao usuário."
)


def _with_preamble(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return (
        msgs
        if any(m.get("role") == "system" for m in msgs)
        else [{"role": "system", "content": _PREAMBLE}] + msgs
    )


def llamacpp_chat(
    messages: List[Dict[str, Any]],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Dict[str, Any]:
    """Minimal chat wrapper returning text, tool calls and usage."""
    global _local_llm, _logged
    messages = _with_preamble(messages)
    stop = ["</toolcall>", "</s>"]
    endpoint = os.getenv("LLM_ENDPOINT")
    model = os.getenv("LLM_MODEL", "llama")
    if endpoint:
        if not _logged:
            print(f"[llm] endpoint={endpoint} model={model}")
            _logged = True
        payload: Dict[str, Any] = {"model": model, "messages": messages, "stop": stop}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        try:
            resp = requests.post(endpoint, json=payload, timeout=60)
            resp.raise_for_status()
        except requests.ConnectionError:  # pragma: no cover - network
            print("[llm] endpoint indisponível → usando fallback local llama_cpp")
        else:
            data = resp.json()
            content = str(data["choices"][0]["message"]["content"])
            text, toolcalls = _parse_toolcalls(content)
            usage = data.get("usage", {})
            return {"text": text, "toolcalls": toolcalls, "usage": usage}
    if _local_llm is None:
        try:
            from llama_cpp import Llama
        except Exception as e:  # pragma: no cover - missing dep
            raise RuntimeError(
                "llama_cpp não disponível; instale ou defina LLM_ENDPOINT"
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
        stop=stop,
    )
    content = str(result["choices"][0]["message"]["content"])
    text, toolcalls = _parse_toolcalls(content)
    usage = result.get("usage", {})
    return {"text": text, "toolcalls": toolcalls, "usage": usage}


def main() -> None:
    sample = "experiments/llm_sandbox/assets/sample.png"
    ensure_sample_png(sample)
    prompts = [
        "Tire um screenshot da tela.",
        "Mostre a posição atual do cursor e faça um crop dessa área.",
        "O que está sob o mouse agora?",
        f"Rode OCR no arquivo {sample}.",
        "Liste os arquivos do diretório atual.",
        "Leia https://example.com e resuma.",
    ]
    agent = Agent(llm=llamacpp_chat, safe_mode=True)  # type: ignore[arg-type]
    results = []
    for p in prompts:
        output = agent.chat(p)
        status = "ok"
        lowered = output.lower()
        if any(k in lowered for k in ("forbidden", "policy")):
            status = "expected_error"
        results.append({"prompt": p, "output": output, "status": status})
    out_path = Path("llm_eval_results.json")
    out_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
