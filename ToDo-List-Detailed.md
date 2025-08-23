# ToDo-List Detalhado: Melhorias para Nu V2 (Milestone LLM)

## Etapa 1 - Ajustes e Refinos (com exemplos)

[x] 1. **agent_local.py** — Sanitizar `name` de tool antes de usar
```python
raw = tc.get("name", "")
name = raw.strip().lower()
if not re.fullmatch(r"[a-z0-9._-]{1,64}", name):
    self.log.warning(json.dumps({"event":"tool_name_invalid","raw":raw}))
    continue
tool = get_tool(name)
```

[x] 2. **agent_local.py** — Redação (PII) antes de `_truncate()`
```python
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_RE_USERPATH = re.compile(r"C:\\Users\\[^\\]+", re.IGNORECASE)
_RE_TOKEN = re.compile(r"(?:api[_-]?key|token|secret)\s*[:=]\s*([A-Za-z0-9._-]{8,})", re.IGNORECASE)

def _redact(text: str) -> str:
    t = _RE_EMAIL.sub("[REDACTED_EMAIL]", text)
    t = _RE_USERPATH.sub("C:\\Users\\<redacted>", t)
    t = _RE_TOKEN.sub(lambda m: m.group(0).replace(m.group(1), "<redacted>"), text)
    return t

payload = _truncate(_redact(raw))
```

[x] 3. **agent_local.py** — Ativar `_shrink()` do contexto
```python
messages = _shrink(messages, max_msgs=20)
```

[x] 4. **agent_local.py** — Cap por reply respeitando quota restante
```python
remaining = self.max_tools - tool_calls_used
if remaining <= 0:
    toolcalls = []
else:
    toolcalls = toolcalls[:remaining]
```

[x] 5. **agent_local.py** — Envelope de erro de tool padronizado
```python
messages.append({
  "role":"tool",
  "name": name,
  "tool_call_id": tool_call_id,
  "content": json.dumps({"kind":"error","code": code, "note":"timeout","retry_safe": False})
})
```

[x] 6. **agent_local.py** — Mensagem humana quando aciona circuit breaker
```python
return "Falhei repetidamente ao usar ferramentas nesta tarefa. Posso tentar outro caminho (sem tools) ou você quer ajustar o pedido?"
```

[x] 7. **agent_local.py** — Headers opcionais para LLM (Auth)
```python
headers = {}
api_key = os.getenv("LLM_API_KEY", "").strip()
auth_hdr = os.getenv("LLM_AUTH_HEADER", "").strip()
if api_key and not auth_hdr:
    headers["Authorization"] = f"Bearer {api_key}"
elif auth_hdr:
    k,v = auth_hdr.split(":",1)
    headers[k.strip()] = v.strip()
resp = requests.post(endpoint, json=payload, headers=headers or None, timeout=timeout)
```

[x] 8. **agent_local.py** — Política de retries curta por tool
```python
retry = int(tool.get("schema",{}).get("x-retry", 0))
attempts = 1 + max(0, retry)
for i in range(attempts):
    result = dispatch(env)
    if result.get("kind") != "error":
        break
    if i+1 < attempts:
        time.sleep(0.2*(i+1))
```

[x] 9. **registry.py** — Políticas por risco de tool
```python
if self.safe_mode and tool.get("safety") == "destructive":
    messages.append({"role":"tool","name":name,"tool_call_id":tool_call_id,
                     "content":json.dumps({"kind":"error","code":"forbidden_in_safe_mode"})})
    continue
```

[x] 10. **agent_local.py** — Validação extra de ranges em schema
```python
minv = spec.get("minimum"); maxv = spec.get("maximum")
if isinstance(val,(int,float)):
    if minv is not None and val < minv: invalid.append(key)
    if maxv is not None and val > maxv: invalid.append(key)
```

[x] 11. **agent_local.py** — Log de `tool_limit_reached` com hash do reply
```python
h = uuid.uuid5(uuid.NAMESPACE_OID, reply).hex[:8]
self.log.info(json.dumps({"event":"tool_limit_reached","reply_hash":h}))
```

[x] 12. **agent_local.py** — Normalizar whitespace de tool replies
```python
text, _ = _parse_toolcalls(final)
return re.sub(r"\s+\n", "\n", text.strip())
```

[ ] 13. **agent_local.py** — Temperatura e max_tokens parametrizáveis  
```python
self.temperature = temperature
self.max_tokens = max_tokens
self.llm(messages, max_tokens=self.max_tokens, temperature=self.temperature)
```

[ ] 14. **settings.py** — Acrescentar chaves para LLM headers  
```python
DEFAULTS.update({"LLM_API_KEY":"", "LLM_AUTH_HEADER":""})
LLM_API_KEY = CONFIG["LLM_API_KEY"]
LLM_AUTH_HEADER = CONFIG["LLM_AUTH_HEADER"]
```

[ ] 15. **dispatcher.py** — Código de erro interno padronizado  
```python
code, msg = err
code = code or "internal"
```

[ ] 16. **dispatcher.py** — Métrica de rate limit com motivo  
```python
metrics.record_route_status(name, "rate_limited")
```

[ ] 17. **metrics.py** — Gauge de tokens_per_sec por LLM isolado  
```python
record_gauge("tokens_per_sec", tps, label=model)
```

[ ] 18. **tests/test_agent_local.py** — Casos extras do parser  
- Vários `<toolcall>` intercalados com texto.  
- JSON malformado (trailing commas, aspas simples).

[ ] 19. **tests/test_agent_local.py** — Safe Mode bloqueando “destructive”  
Simular tool com `safety="destructive"`, garantir erro padronizado.

[ ] 20. **registry.py** — Alias/versão para tools (futuro)  
```python
REGISTRY[alias] = REGISTRY[name]
```

[ ] 21. **agent_local.py** — Dry-run de toolcalls  
```python
if getattr(self, "dry_run", False):
    messages.append({"role":"tool","name":name,"tool_call_id":tool_call_id,
                     "content":json.dumps({"kind":"ok","dry_run":True,"args":args})})
    continue
```

[ ] 22. **agent_local.py** — Mensagem curta ao modelo quando safe_mode bloqueia  
```python
messages.append({"role":"tool","name":name,"tool_call_id":tool_call_id,
                 "content":json.dumps({"kind":"error","code":"forbidden_in_safe_mode",
                                       "hint":"peça confirmação ou proponha alternativa"})})
```

[ ] 23. **agent_local.py** — Hash de conteúdo pesado em logs  
```python
raw_hash = hashlib.sha256(raw.encode("utf-8","ignore")).hexdigest()[:12]
self.log.info(json.dumps({"event":"tool_result","name":name,"hash":raw_hash,"size":len(raw)}))
payload = _truncate(_redact(raw))
```

[ ] 24. **settings.py** — Limites separados para log e retorno ao modelo  
```python
DEFAULTS.update({"MAX_LOG_CHARS": 2000})
MAX_LOG_CHARS = CONFIG["MAX_LOG_CHARS"]
```

[ ] 25. **agent_local.py** — Aplicar MAX_LOG_CHARS nos logs  
```python
short = payload[:settings.MAX_LOG_CHARS]
self.log.info(json.dumps({"event":"tool_result","preview":short}))
```

[ ] 26. **agent_local.py** — Telemetria de “remaining_tools”  
```python
messages.append({"role":"system","content":f"[remaining_tools={remaining}]"})
```

[ ] 27. **settings.py** — SAFE_MODE_DEFAULT_POLICY (string)  
```python
DEFAULTS.update({"SAFE_MODE_DEFAULT_POLICY":"block_destructive"})
SAFE_MODE_DEFAULT_POLICY = CONFIG["SAFE_MODE_DEFAULT_POLICY"]
```

[ ] 28. **dispatcher.py** — Return detail em timeout  
```python
return {"kind":"error","code":"timeout","elapsed_ms":elapsed_ms}
```

[ ] 29. **agent_local.py** — Normalizar whitespace de tool replies (extra)  
```python
content = re.sub(r"\s{3,}", "  ", content)
```

[ ] 30. **milestone_llm.md** — Atualizar DoD da Etapa 1  
Adicionar bullets: shrink, redact, cap por reply, headers LLM, erro padronizado.
