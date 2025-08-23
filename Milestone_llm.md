# Roadmap LLM Nu v2 (Agente + Núcleo + Runtime)

Este roadmap organiza as entregas em quatro marcos (LLM-0 → LLM-3) com tarefas acionáveis, critérios de pronto (DoD) e dependências. Use este arquivo como *issue tracker* inicial e referência para milestones do GitHub.

Sempre que terminar um minor‑milestone, coloque “X” dentro do `[ ]`.

## 🎯 Objetivo
A **Nu v2 (LLM)** é o motor conversacional que planeja e age sobre o computador com segurança, usando as *tools* expostas pelo núcleo (M2).
O propósito final é **conversar naturalmente**, **observar a tela/arquivos**, **pesquisar**, **tomar decisões** e, quando permitido, **executar ações** (abrir, clicar, digitar, editar arquivos), sempre sob **SAFE_MODE** e políticas claras.

Combina:
- **Planejamento conversacional** (*explain-first*, pedir confirmação, dividir tarefas).
- **Ferramentas tipadas** do núcleo (via `dispatch()`), com **IDs opacos** e cache para endereçar janelas/controles.
- **Políticas de segurança** (allowlists, confirmações, rate-limit, SAFE_MODE).
- **Telemetria** para explicar decisões e medir qualidade.

Os milestones LLM-0…LLM-3 representam a evolução de um **agente local** → **agente com ações seguras** → **memória/planejamento** → **runtime HTTP/orquestração**.

---

## ✅ Dependências já prontas (do M2)
- Núcleo: `registry.py`, `dispatcher.py`, `tools/*`, `policy.py` (roteamento mínimo).
- Endpoints opcionais: `/v1/tools.list` e `/v1/tools.call` (com auth/limites).
- SAFE_MODE, rate‑limit por tool, timeouts, SSRF/ZIP hardening.
- IDs opacos e cache `ID→bounds`.

---

## Milestone LLM-0 — **Agente local (explain-first + tools read‑only)**
**Objetivo:** rodar a LLM **localmente**, decidir quando usar ferramentas e executar até **3** chamadas por turno via `dispatch()` **em processo** (sem HTTP).

- [x] **Etapa 1: Loop do agente + parser de toolcall**
  Arquivos: `agent_local.py`
  **DoD:**
  - suporte a `<toolcall>{ "name": "...", "args": {...} }</toolcall>`
  - no máx. **3** chamadas por turno
  - truncar payloads grandes antes de devolver ao modelo
  - parametrizar backend por **`LLM_ENDPOINT`** e **`LLM_MODEL`**
  - reduzir contexto via `_shrink()`
  - redigir PII antes de truncar (`_redact`)
  - cap por reply respeitando quota restante
  - headers opcionais para LLM
  - envelope de erro padronizado
  **Prioridade:** P0 • **Size:** S

- [x] **Etapa 2: Policy *explain‑first* (gates)**
  Arquivos: `policy.py`  
  **DoD:**  
  - Perguntas **conceituais/estáveis** → **sem tool**.  
  - Conteúdo **recente** (preço/notícia/tempo) → `web.*`.  
  - **Pedido explícito** de screenshot/OCR/ZIP → tool correspondente.  
  - Bloqueio de operações destrutivas com `forbidden` (SAFE_MODE).  
  - **Tool adicional para contexto do ambiente:** `system.info` (read‑only) retornando OS/CPU/RAM/GPU/monitores/`safe_mode` para orientar o planejamento sem expor IP.  
  **Prioridade:** P0 • **Size:** S

- [x] **Etapa 3: Telemetria do agente**
  Arquivos: `agent_local.py`, `metrics.py`  
  **DoD:** registrar `agent_turn_ms`, `agent_tool_uses_total`, `agent_policy_blocks_total{reason}`; logar por chamada `tool_name`, `latency_ms`, `outcome`.  
  **Prioridade:** P1 • **Size:** S

- [ ] **Etapa 4: Testes E2E mínimos (sem rede real)**  
  Arquivos: `tests/test_agent_local.py`  
  **DoD:**  
  - “O que é entropia?” → resposta **sem** tool.  
  - “dólar hoje?” → exatamente **1** chamada `web.read` (stub) e citação da fonte/data.  
  - Pedido de tool **não planejada** → bloqueio por policy (`forbidden`).  
  **Prioridade:** P0 • **Size:** S

**Metas de qualidade (LLM‑0 DoD global):**
- ≥ **90%** das perguntas conceituais resolvidas **sem** tool.  
- ≥ **90%** de consultas “recente” com **1** tool `web.*` e **fonte/data** citadas.  
- **Nunca** ultrapassar **3** toolcalls por turno.  

> Observação: Ferramentas de **ação** (click/type/open/write) **ficam para LLM‑1**. Se desejar já suportar “criar um arquivo” sem tocar no sistema, habilite **opcionalmente** a tool `doc.ppt_generate` que salva **apenas** em `exports/` (SAFE_MODE on).

---

## Milestone LLM-1 — **Ações seguras (HITL + SAFE_MODE)**
**Objetivo:** habilitar ações modificadoras com confirmação (*human‑in‑the‑loop*), alvo por `window_id/control_id` e “dry‑run” por padrão.

- [ ] **Etapa 1a: Geração de documentos segura (opcional)**  
  Arquivos: `tools/ppt.py`, `registry.py`, `tools/__init__.py`, `settings.py`  
  **DoD:** `doc.ppt_generate` cria `.pptx` a partir de `slides[]/images[]/citations[]`, gravando **somente** em `EXPORTS_DIR`; mantido em **SAFE_MODE=True**.  
  **Prioridade:** P1 • **Size:** S

- [ ] **Etapa 1b: Adapters de ação (read‑only → write)**  
  Arquivos: `tools/actions.py` (novo), `uia.py`  
  **DoD:** `ui.click`, `ui.type_text`, `app.open`, `fs.write` (allowlists), aceitando `window_id/control_id` **ou** `bounds`.  
  **Prioridade:** P0 • **Size:** M

- [ ] **Etapa 2: Confirmação & SAFE_MODE**  
  Arquivos: `agent_local.py`, `policy.py`  
  **DoD:** antes de executar ação destrutiva: gerar **plano** + **diff** curto e pedir **CONFIRMAR**; em `SAFE_MODE=True` retornar `forbidden`.  
  **Prioridade:** P0 • **Size:** S

- [ ] **Etapa 3: Alvo estável & heurística de foco**  
  Arquivos: `resolve.py`, `tools/actions.py`  
  **DoD:** quando `control_id` não estiver em cache, re‑resolver via caminho UIA; se falhar, degradar para heurística por `control_type/name/value`.  
  **Prioridade:** P1 • **Size:** M

- [ ] **Etapa 4: Testes E2E de ação**  
  Arquivos: `tests/test_actions.py`  
  **DoD:** cenários “click em Edit”, “type_text seguro”, “fs.write bloqueado por SAFE_MODE”, “confirm‑then‑apply”.  
  **Prioridade:** P0 • **Size:** M

**Dependências:** LLM‑0 concluído; IDs/caches do M2.

---

## Milestone LLM-2 — **Memória & planejamento multi‑turn**
**Objetivo:** melhorar continuidade e qualidade: memória curta de sessão, perguntas de esclarecimento e decomposição de tarefas.

- [ ] **Etapa 1: Memória curta (working memory)**  
  Arquivos: `agent_local.py`  
  **DoD:** manter últimos *N* passos (texto + toolcalls); resumos automáticos quando passar de *N*.  
  **Prioridade:** P1 • **Size:** S

- [ ] **Etapa 2: Clarificações automáticas**  
  Arquivos: `policy.py`  
  **DoD:** detectar ambiguidade (alvo não resolvido, múltiplos matches) e **perguntar** antes de agir; limite de 1 follow‑up.  
  **Prioridade:** P1 • **Size:** S

- [ ] **Etapa 3: Planos curtos (2–5 passos)**  
  Arquivos: `agent_local.py`  
  **DoD:** antes de múltiplas tools, produzir “Plano:” (lista curta) → executar → “Resultado:” com verificação final.  
  **Prioridade:** P2 • **Size:** M

- [ ] **Etapa 4: Avaliação automática (harness A/B)**  
  Arquivos: `tools/eval.py` (novo), `tests/test_eval_scenarios.py`  
  **DoD:** *harness* que roda ~10 prompts e mede: **% de sucesso**, nº de toolcalls, latência média; compara **modelos/backends** (ex.: Mistral‑7B vs Llama‑3‑8B).  
  **Prioridade:** P2 • **Size:** M

---

## Milestone LLM-3 — **Runtime HTTP & orquestração**
**Objetivo:** expor o agente para clientes externos e/ou usar LLM remota com controle fino de custo/latência.

- [ ] **Etapa 1: Bridge HTTP do agente (opcional)**  
  Arquivos: `api.py`, `agent_service.py` (novo)  
  **DoD:** `POST /v1/agent.chat` (SSE opcional) usando o **mesmo** núcleo/Policy; auth por API key; CORS configurável; limites de payload.  
  **Prioridade:** P2 • **Size:** M

- [ ] **Etapa 2: Multi‑modelo/estratégias**  
  Arquivos: `agent_local.py`, `settings.py`  
  **DoD:** seleção de backend (local/remoto), *fallback* e *time‑budget* por tipo de tarefa (web/ocr/planejamento).  
  **Prioridade:** P3 • **Size:** M

- [ ] **Etapa 3: Observabilidade & auditoria**  
  Arquivos: `metrics.py`, `logger.py`  
  **DoD:** span por turno com `tool_calls_total{tool,outcome}`, `tool_latency_ms`, `agent_turn_ms`; trilhas de decisão (motivos da Policy).  
  **Prioridade:** P2 • **Size:** S

**Dependências:** LLM‑0 concluído; M2 disponível (dispatcher/tools).

---

## 🧪 Critérios gerais de pronto (DoD)
- Testes unitários e E2E verdes (`pytest -q`) e *smoke* local do agente.
- `mypy` no modo gradual: sem novos *Any* “soltos” nos módulos do agente.
- Contratos estáveis: envelopes `ok|error` e códigos (`bad_args`, `not_found`, `forbidden`, `rate_limit`, `timeout`, `tool_error`).
- SAFE_MODE respeitado por padrão; ações destrutivas exigem confirmação explícita.
- Métricas essenciais expostas no `/metrics` (quando em modo API).

---

## 🔗 Referências internas
- Núcleo: `registry.py`, `dispatcher.py`, `tools/*`, `policy.py`
- Agente: `agent_local.py`
- HTTP opcional: `api.py` (`/v1/tools.*`, `/v1/agent.chat` se ativado)
- Segurança: `settings.py` (SAFE_MODE, allowlists, API_KEY, EXPORTS_DIR)

> Observação: se a LLM rodar **localmente**, o agente fala direto com `dispatch()` (sem HTTP). O runtime HTTP (LLM‑3) é opcional e serve para integração com outros clientes.
