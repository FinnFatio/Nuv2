from __future__ import annotations

# --- ensure repo root on sys.path ---
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# ------------------------------------

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests  # type: ignore[import-untyped]

from agent_local import Agent, _parse_toolcalls

SAMPLE_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y0bZ9wAAAAASUVORK5CYII="
)  # PNG 1x1


def ensure_sample_png(path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_bytes(base64.b64decode(SAMPLE_PNG_B64))


_logged = False


# substitua a função llamacpp_chat por esta versão com fallback local
_local_llm = None

def llamacpp_chat(
    messages: List[Dict[str, Any]],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Dict[str, Any]:
    """Chat wrapper com STOP e fallback p/ llama_cpp local quando não há endpoint."""
    global _local_llm, _logged
    stop = ["</toolcall>", "</s>"]
    endpoint = os.getenv("LLM_ENDPOINT", "").strip() or None
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
            data = resp.json()
            content = str(data["choices"][0]["message"]["content"])
            text, toolcalls = _parse_toolcalls(content)
            usage = data.get("usage", {})
            return {"text": text, "toolcalls": toolcalls, "usage": usage}
        except requests.ConnectionError:
            print("[llm] endpoint indisponível → usando fallback local llama_cpp")

    # fallback local (llama_cpp)
    if _local_llm is None:
        print(f"[llm] local model={model}")
        from llama_cpp import Llama  # requer: pip install llama-cpp-python
        # pode ler N_CTX/N_THREADS/N_GPU_LAYERS se quiser
        _local_llm = Llama(model_path=model, verbose=False)
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
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
