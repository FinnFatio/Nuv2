from __future__ import annotations

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


def llamacpp_chat(
    messages: List[Dict[str, Any]],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Dict[str, Any]:
    """Minimal chat wrapper returning text, tool calls and usage."""
    global _logged
    endpoint = os.getenv("LLM_ENDPOINT", "http://localhost:8080/v1/chat/completions")
    model = os.getenv("LLM_MODEL", "llama")
    if not _logged:
        print(f"[llm] endpoint={endpoint} model={model}")
        _logged = True
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stop": ["</toolcall>", "</s>"],
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature
    try:
        resp = requests.post(endpoint, json=payload, timeout=60)
        resp.raise_for_status()
    except requests.ConnectionError as e:  # pragma: no cover - network
        raise RuntimeError("Falha ao conectar ao endpoint LLM") from e
    data = resp.json()
    content = str(data["choices"][0]["message"]["content"])
    text, toolcalls = _parse_toolcalls(content)
    usage = data.get("usage", {})
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
