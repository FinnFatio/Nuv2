# Roadmap Nu v2 — Núcleo LLM

Este roadmap detalha os marcos de desenvolvimento do agente LLM local, ações seguras, memória e runtime HTTP, com tarefas acionáveis, critérios de pronto (DoD) e dependências.

---

## Milestone LLM-0 — Agente local (explain-first + tools read-only)
**Objetivo:** rodar a LLM localmente, decidir quando usar ferramentas e executar até 3 chamadas por turno via `dispatch()` em processo (sem HTTP).

- **Etapa 1: Loop do agente + parser de toolcall**
  - **Arquivo:** `agent_local.py`
  - **DoD:** suporte a `<toolcall>{ "name": "...", "args": {...} }</toolcall>`, no máx. 3 chamadas por turno; truncar payloads grandes antes de devolver ao modelo.
  - **Prioridade:** P0 • **Size:** S

- **Etapa 2: Policy explain-first (gates)**
  - **Arquivo:** `policy.py`
  - **DoD:**
    - Conceitual/estável → sem tool
    - Conteúdo recente (preço/notícia/tempo) → `web.*`
    - Pedido explícito de screenshot/OCR/ZIP → tool correspondente
    - Bloqueio de destrutivas com forbidden (`SAFE_MODE`)
  - **Prioridade:** P0 • **Size:** S

- **Etapa 3: Telemetria do agente**
  - **Arquivos:** `agent_local.py`, `metrics.py`
  - **DoD:** `agent_turn_ms`, `agent_tool_uses_total`, `agent_policy_blocks_total{reason}`; logar `tool_name`, `latency_ms`, `outcome`.
  - **Prioridade:** P1 • **Size:** S

- **Etapa 4: Testes E2E mínimos (sem rede real)**
  - **Arquivo:** `tests/test_agent_local.py`
  - **DoD:**
    - “O que é entropia?” → resposta sem tool.
    - “dólar hoje?” → 1 chamada `web.read` (stub) e citação da fonte.
    - Pedido de tool não planejada → bloqueio por policy.
  - **Prioridade:** P0 • **Size:** S

**Notas:** Backend LLM local via Ollama (padrão) ou llama-cpp; os toolcards são curtos (sem schemas completos) para economizar contexto.

---

## Milestone LLM-1 — Ações seguras (HITL + SAFE_MODE)
**Objetivo:** habilitar ações modificadoras com confirmação (human-in-the-loop), alvo por `window_id`/`control_id` e “dry-run” por padrão.

- **Etapa 1: Adapters de ação (read-only → write)**
  - **Arquivos:** `tools/actions.py` (novo), `uia.py`
  - **DoD:** `ui.click`, `ui.type_text`, `app.open`, `fs.write` (allowlists), aceitando `window_id`/`control_id` ou `bounds`.
  - **Prioridade:** P0 • **Size:** M

- **Etapa 2: Confirmação & SAFE_MODE**
  - **Arquivos:** `agent_local.py`, `policy.py`
  - **DoD:** antes de executar ação destrutiva: gerar plano + diff curto e pedir CONFIRMAR; em `SAFE_MODE=True` retornar forbidden.
  - **Prioridade:** P0 • **Size:** S

- **Etapa 3: Alvo estável & heurística de foco**
  - **Arquivos:** `resolve.py`, `tools/actions.py`
  - **DoD:** quando `control_id` não estiver em cache, re-resolver via caminho UIA; se falhar, degradar para heurística por `control_type`/`name`/`value`.
  - **Prioridade:** P1 • **Size:** M

- **Etapa 4: Testes E2E de ação**
  - **Arquivo:** `tests/test_actions.py`
  - **DoD:** cenários “click em Edit”, “type_text seguro”, “fs.write bloqueado por SAFE_MODE”, “confirm-then-apply”.
  - **Prioridade:** P0 • **Size:** M

**Dependências:** LLM-0 concluído; IDs/caches do M2.

---

## Milestone LLM-2 — Memória & planejamento multi-turn
**Objetivo:** melhorar continuidade e qualidade: memória curta de sessão, perguntas de esclarecimento e decomposição de tarefas.

- **Etapa 1: Memória curta (working memory)**
  - **Arquivo:** `agent_local.py`
  - **DoD:** manter últimos N passos (text + toolcalls); resumos automáticos quando passar de N.
  - **Prioridade:** P1 • **Size:** S

- **Etapa 2: Clarificações automáticas**
  - **Arquivo:** `policy.py`
  - **DoD:** detectar ambiguidade (alvo não resolvido, múltiplos matches) e perguntar antes de agir; limite de 1 follow-up.
  - **Prioridade:** P1 • **Size:** S

- **Etapa 3: Planos curtos (2–5 passos)**
  - **Arquivo:** `agent_local.py`
  - **DoD:** antes de múltiplas tools, produzir “Plano:” (lista curta) → executar → “Resultado:” com verificação final.
  - **Prioridade:** P2 • **Size:** M

- **Etapa 4: Avaliação automática**
  - **Arquivos:** `tools/eval.py` (novo), `tests/test_eval_scenarios.py`
  - **DoD:** harness que roda cenários (ex.: “pega o preço e registra em .txt”), medindo sucesso, nº de toolcalls e latência.
  - **Prioridade:** P2 • **Size:** M

---

## Milestone LLM-3 — Runtime HTTP & orquestração
**Objetivo:** expor o agente para clientes externos e/ou usar LLM remota com controle fino de custo/latência.

- **Etapa 1: Bridge HTTP do agente (opcional)**
  - **Arquivos:** `api.py`, `agent_service.py` (novo)
  - **DoD:** `POST /v1/agent.chat` (SSE opcional) usando o mesmo núcleo/Policy; auth por API key; CORS configurável; limites de payload.
  - **Prioridade:** P2 • **Size:** M

- **Etapa 2: Multi-modelo/estratégias**
  - **Arquivos:** `agent_local.py`, `settings.py`
  - **DoD:** seleção de backend (local/remoto), fallback e time-budget por tipo de tarefa (`web`/`ocr`/planejamento).
  - **Prioridade:** P3 • **Size:** M

- **Etapa 3: Observabilidade & auditoria**
  - **Arquivos:** `metrics.py`, `logger.py`
  - **DoD:** span por turno com `tool_calls_total{tool,outcome}`, `tool_latency_ms`, `agent_turn_ms`; trilhas de decisão (motivos da Policy).
  - **Prioridade:** P2 • **Size:** S

**Dependências:** LLM-0 concluído; M2 disponível (dispatcher/tools).

---

## Extras & Notas
- Backend LLM local via Ollama (padrão) ou llama-cpp ou llama-server.
- Toolcards são curtos (sem schemas completos) para economizar contexto.
- IDs/caches do M2 são necessários para ações seguras.