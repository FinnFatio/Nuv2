# Roadmap Nu v2 (Visor → Runtime)

Este roadmap organiza as entregas em quatro marcos (M0–M3) com tarefas acionáveis, critérios de pronto (DoD) e dependências. Use este arquivo como issue tracker inicial e referência para milestones do GitHub.

Sempre que terminar um minor-milestone, colocar " X " dentro do " [ ] "
---

## Milestone M0 — Visor confiável (higiene básica)
**Objetivo:** garantir que “o que está debaixo do mouse?” funcione de forma estável em qualquer monitor.

 - [X] **Tornar o processo DPI-aware**
    Arquivo: `cursor.py` (setup de processo, antes de `GetCursorPos`)
    **DoD:** coordenadas do cursor batem em 100%/125%/150% de escala; teste em 1+ monitores.
    **Prioridade:** P0 • **Size:** S

- [ ] **Migrar captura para `mss` (multi-monitor)**  
  Arquivo: `screenshot.py`  
  **DoD:** `capture()` e `capture_around()` funcionam em setups multi-monitor; p95 < 25ms para região 300×120.  
  **Prioridade:** P0 • **Size:** M

- [ ] **Configurar Tesseract (path/idioma/opções)**  
  Arquivos: `ocr.py`, `settings.py`  
  **DoD:** erro claro se binário ausente; idioma padrão `por+eng`; flags `--oem 3 --psm 6` configuráveis; retorna confiança > 0 em texto simples.  
  **Prioridade:** P0 • **Size:** S

- [ ] **Clampar região de captura aos bounds da tela**  
  Arquivo: `screenshot.py`  
  **DoD:** `capture_around()` nunca retorna bbox negativa/fora de tela; cantos funcionam.  
  **Prioridade:** P0 • **Size:** S

- [ ] **Logging estruturado (JSONL) + tempos**  
  Arquivo: ponto central em `resolve.py` (ou `logger.py`/middleware)  
  **DoD:** cada chamada a `describe_under_cursor()` emite eventos `{stage: "uia|screenshot|ocr|total", elapsed_ms, ok, err}` em JSONL.  
  **Prioridade:** P0 • **Size:** S

---

## Milestone M1 — Visão útil (UIA rica + fusão decente)
**Objetivo:** enriquecer metadados e escolher melhor entre UIA e OCR.

- [ ] **Enriquecer UIA (AutomationId, patterns, flags)**  
  Arquivo: `uia.py`  
  **DoD:** JSON inclui `automation_id`, `name`, `value` (quando houver), `control_type`, `is_enabled`, `is_offscreen`, `patterns[]`, `window:{handle, active}`.  
  **Prioridade:** P0 • **Size:** M

- [ ] **OCR com recorte pelo elemento + heurística de fusão**  
  Arquivos: `resolve.py`, `ocr.py`, `screenshot.py`  
  **DoD:** se há `bounds` do elemento, OCR recorta dentro; heurística usa `is_offscreen`, `control_type`, `value/name` para definir `text.chosen` e `text.source∈{uia,ocr}`; threshold em `settings.py`.  
  **Prioridade:** P1 • **Size:** M

- [ ] **Telemetria consolidada**  
  Arquivos: `resolve.py`  
  **DoD:** métricas agregadas: `time_cursor`, `time_uia`, `time_capture`, `time_ocr`; contadores de fallback (vezes que caiu em OCR).  
  **Prioridade:** P1 • **Size:** S

- [ ] **Config externa centralizada**  
  Arquivos: `settings.py`  
  **DoD:** `.env/config.json` controlam: idioma OCR, box padrão (W×H), thresholds, hz do `hover_watch`, flags `run_as_admin`, etc.  
  **Prioridade:** P1 • **Size:** S

---

## Milestone M2 — Operabilidade (CLIs + IDs estáveis)
**Objetivo:** facilitar uso e permitir referência a elementos entre chamadas.

- [ ] **IDs opacos e cache mínimo de estado**  
  Arquivos: `uia.py`, `resolve.py`  
  **DoD:** gerar `window_id` e `control_id` estáveis (hash de `pid + path UIA + automation_id`); expor `state_digest` com `last_window_id`, `last_editable_control_id`.  
  **Prioridade:** P0 • **Size:** M

- [ ] **CLIs auxiliares**  
  Arquivos: `hover_watch.py`, `inspect_point.py`, (novo) `screenshot_cli.py`  
  **DoD:**  
    - `hover_watch --hz 2` → JSONL contínuo do alvo (com tempos/erros).  
    - `inspect --point x,y` → mesmo JSON do under-mouse, para coordenadas arbitrárias.  
    - `screenshot --active|--window "re"|--region x,y,w,h` → salva PNG.  
  **Prioridade:** P1 • **Size:** S

---

## Milestone M3 — Runtime HTTP (ponte)
**Objetivo:** expor a visão como serviço para futuros planners/LLMs.

- [ ] **Serviço HTTP mínimo de inspeção e snapshot**  
  Arquivo: `api.py`  
  **DoD:**  
    - `GET /inspect?x=&y=` → JSON do alvo (igual ao CLI).  
    - `GET /details?id=` → campos extra/affordances do elemento.  
    - `GET /snapshot?id|region=` → PNG (`image/png`).  
    - Logs e métricas idênticos aos CLIs; CORS desativado por padrão.  
  **Prioridade:** P0 • **Size:** M

---

## Extras (nice-to-have, pós-M3)
- Admin-helper: script para lançar o processo “como admin” quando necessário para UIA completa (Windows).  
- Detector de monitores: endpoint `GET /monitors` com bounds de cada tela (ajuda a depurar clamp).  
- Perfil de performance: contador de GC, memória e FPS do `hover_watch`.  
- Test kit manual: cenários guiados (Notepad, Explorer, Edge) para validar `uia_conf` vs `ocr_conf`.

---

## Labels sugeridas (para issues)
- `priority:P0|P1`  
- `size:S|M|L`  
- `area:UIA|OCR|Screenshot|API|DX|Telemetry`  
- `milestone:M0|M1|M2|M3`

---

## Dependências (ordem lógica)
- M0 antes de tudo (DPI/mss/config/logs).  
- M1 depende de M0 (UIA rica precisa de captura/ocr confiáveis).  
- M2 depende de M1 (IDs estáveis exigem UIA robusto).  
- M3 depende de M2 (expor via API só depois da visão madura).
