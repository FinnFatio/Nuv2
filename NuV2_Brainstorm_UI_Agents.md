# Nu v2 — Brainstorm de Interação com Aplicativos (visão + hover + screenshot)

> **Escopo:** consolidar as ideias a partir do brainstorm sobre como a Nu deve operar apps com `screenshot`, `hover` e `what_under_mouse`, e quando introduzir ferramentas que abrem apps/arquivos (LLM‑1). Documento técnico, mas sem implementação.

---

## 1) Posição no roadmap (LLM‑0 → LLM‑1)

- **LLM‑0 (agora):** loop do agente, parser `<toolcall>`, safe mode, truncagem, tools “seguras/sandbox” (ex.: `echo`, `math.add`, `fs.write` limitado). **Não** abre programas/arquivos ainda.
- **LLM‑1 (próximo):** entra o conjunto de **adapters de ação** para mexer em apps/arquivos/janelas, com visão contínua (`screenshot/hover/what_under_mouse`), confirmações e **guardrails**.

**Decisão:** deixar os adapters de ação para **LLM‑1 P0**, mantendo o LLM‑0 limpo e testável.

---

## 2) Princípios de operação com UI (visão‑primeiro)

1. **Ver → Agir → Ver**: antes de agir, **print do estado**; depois de agir, **print de confirmação**. Comparar “esperado vs observado”.
2. **Hover como confirmação “soft”**: antes do clique, **hover** no alvo e checagem com `what_under_mouse` (rótulo, tooltip, role). Se não bater, **não clica**.
3. **Clique em dois tempos**: *pré‑clique* (hover + checagem) → *clique* → *pós‑clique* (mini‑screenshot/crop da região para validar o efeito).
4. **Mini‑prints (crops)**: **screenshot completo** só em troca de janela/app. Nos passos locais, **crops** pequenos da área alvo para reduzir ruído.
5. **Plano visível**: para ações com risco, mostrar um **micro‑roteiro** do que fará (ex.: “focar Notepad → apontar ‘Salvar’ → confirmar por hover → clicar”). Executar **após confirmação**.
6. **Pergunta única e precisa**: em ambiguidade (“dois ‘OK’”), **uma pergunta** com crop: “é este da esquerda?” — evita interrogatório.
7. **Detectar “nada aconteceu”**: se o estado não mudou, **parar** e mostrar antes/depois. Oferecer alternativas: alvo vizinho, rolagem, focar janela.
8. **Pop‑ups/diálogos**: pós‑click propenso a diálogo → print rápido; se for “Salvar alterações?”, **voltar ao usuário** antes de qualquer ação destrutiva.
9. **Lista branca de intenções**: palavras de risco (“Excluir”, “Formatar”, “Sair sem salvar”) **sempre** exigem confirmação explícita.
10. **Memória visual**: ao confirmar “é esse botão”, registrar “caminho visual” (título/estrutura) para repetir mais rápido **sem perder a checagem via hover**.
11. **Painel “o que estou vendo”**: manter estado atual visível (app, janela, alvo, crop de evidência) para depuração humana rápida.
12. **Failsafe**: se `screenshot`/`what_under_mouse` falhar, **não agir no escuro**. “Não consegui ver a tela; tentamos de novo ou rodo em modo observador?”
13. **Privacidade**: capturar **apenas** a janela alvo/recorte; **redigir** conteúdo sensível nos logs e **descartar** prints antigos.
14. **Ritmo humano**: movimento curto, pequeno hover para tooltip, **um clique**; evitar “rajada” de cliques.
15. **Modo Observador**: opção “me mostre como faria” (só hover + prints) — útil para treino/confiança.

---

## 3) Adapters de ação (LLM‑1 P0) — Especificação proposta

> Entram **apenas** no LLM‑1, todos com **safe_mode ON** por padrão, **allowlist** e `dry_run` por default.

### 3.1 `app.open`
- **Objetivo:** abrir executável/arquivo via shell.
- **Args:** `target:str` (path/alias), `args?:str`, `cwd?:str`, `wait?:bool=false`, `timeout_ms?:int`, `dry_run?:bool=true`
- **Segurança:** em *safe_mode*, só `target` na **allowlist** (`ALLOWED_APPS`) ou em diretórios permitidos.

**Exemplo**
```xml
<toolcall>{"name":"app.open","args":{"target":"notepad.exe","dry_run":true}}</toolcall>
```

### 3.2 `file.open_with`
- **Objetivo:** abrir arquivo com app padrão do sistema (duplo clique).
- **Args:** `path:str`, `dry_run?:bool=true`
- **Segurança:** extensões e pastas permitidas (ex.: `Documents`, `Desktop`).

**Exemplo**
```xml
<toolcall>{"name":"file.open_with","args":{"path":"C:\Users\Claudio\Documents\todo.md","dry_run":true}}</toolcall>
```

### 3.3 `app.focus`
- **Objetivo:** trazer uma janela à frente.
- **Args:** `title?:str`, `process_name?:str`

### 3.4 `app.close`
- **Objetivo:** fechar janela/app.
- **Args:** `pid?:int`, `title?:str`, `force?:bool=false`
- **Segurança:** `force` **bloqueado** em safe_mode; perguntar se há mudanças não salvas.

### 3.5 (Opcional) `shell.run`
- **Objetivo:** executar comando **allowlisted**.
- **Args:** `cmd:str`, `args?:str`, `dry_run?:bool=true`, `timeout_ms?:int`
- **Segurança:** estritamente por allowlist; `dry_run` padrão; sempre pede confirmação.

---

## 4) Descoberta & UX (mostrar “o que dá pra fazer”)

1. **Mapa do PC visível**: apps favoritos/recorrentes, atalhos (editor, bloco, navegador), pastas‑chave e **arquivos recentes**.
2. **Comandos naturais + apelidos**: “abra meu editor/bloco/navegador”; Nu aprende apelidos (editor=VS Code, bloco=Notepad…).
3. **Modos claros**: **Observador** (simula), **Executar com confirmação** (pede “posso?”), **Automático (temporário)** para repetitivas.
4. **Vitrine**: 5–7 cartões: Abrir app, Abrir arquivo recente, Fixar atalho, Procurar por nome, Trazer janela pra frente.
5. **Pergunta única**: vago → **uma pergunta** com crop (“este arquivo?”).
6. **Erro confiável**: “não encontrei X. procurar por nome ou escolher na lista?”
7. **Preferências viram padrão**: “.md no VS Code”, “PDF no leitor X”, “sempre confirmar ao fechar app”.
8. **Trilho de segurança**: “não fecho com mudanças não salvas”, “não mato processos”, “não opero fora de Documentos sem você pedir”.
9. **Descoberta amigável**: pedido inexistente → **instalar**, **alternativa** ou **abrir Programas**.
10. **Onboarding 2 min**: 3 apps favoritos? criar atalhos?
11. **Relato pós‑ação**: “abri VS Code com ‘NuV2’. fixar nos recentes?”
12. **Ensine a Nu**: “quando eu falar ‘anotações’, abra o Obsidian” (alias).
13. **Treino seguro**: botão “3 coisas que consigo fazer agora” em **Observador**.

---

## 5) Estratégia de tokens (~8k)

1. **Delta, não novela**: registrar **apenas mudanças**.
2. **Evidência mínima**: referenciar **IDs** (`img#12`, `crop#12b`) + 1–2 palavras (“botão ‘Salvar’”).
3. **Roteiro 3 linhas**: `plano | fez | resultado`.
4. **Tags curtas**: `[ok] [miss] [retry:1] [confirm?] [ambíguo]`.
5. **Handles**: `@notepad`, `@dialog_salvar`, `@btn_salvar`.
6. **Resumo periódico**: a cada 3–4 passos, compactar em 2 bullets.
7. **Políticas fora do turno**: só mencionar ao mudar de modo.
8. **OCR cirúrgico**: extrair só rótulo/título decisivo.
9. **Orçamento**: **150–300 tokens/passo** (plano+evidência+resultado).
10. **Fallback**: “nada aconteceu” → mostrar antes/depois em 1 linha + **2 rotas**.

---

## 6) Modos & confirmação

- **Observador**: só hovers + prints; zero cliques.  
- **Execução com confirmação**: mostra roteiro e espera OK para sensíveis.  
- **Automático (temporário)**: janela de tempo para repetitivas seguras.

**Gatilhos que sempre pedem confirmação**: “Excluir”, “Remover”, “Forçar”, “Sair sem salvar”, “Formatar”, “Encerrar processo”.

---

## 7) Telemetria & logs (alto nível)

- **Por passo**: `{app, janela, ação, alvo, tags, latency_ms, img_id/crop_id}`  
- **Erros**: anexar antes/depois + alternativa escolhida  
- **Privacidade**: redigir dados sensíveis; descartar prints antigos; logs mínimos por padrão

---

## 8) Futuro (fora do escopo imediato)

- **Voz**: `microfone → VAD → STT → REPL → TTS` com hotkey.  
- **Quem‑é‑quem**: diarização/speaker‑ID para marcar `[Claudio]`, `[Convidado]`.  
- **Só após LLM‑1 sólido**.

---

## 9) Exemplos de toolcalls (pseudo‑protocolo)

### A — Abrir Notepad (seguro)
```xml
# plano: focar desktop → abrir notepad (dry_run) → confirmar via hover → executar
<toolcall>{"name":"app.open","args":{"target":"notepad.exe","dry_run":true}}</toolcall>
# após OK:
<toolcall>{"name":"app.open","args":{"target":"notepad.exe","dry_run":false}}</toolcall>
```

### B — Abrir arquivo (observador)
```xml
<toolcall>{"name":"file.open_with","args":{"path":"C:\Users\Claudio\Documents\todo.md","dry_run":true}}</toolcall>
```

### C — Fechar app com segurança
```xml
<toolcall>{"name":"app.close","args":{"title":"Sem título - Bloco de Notas","force":false}}</toolcall>
# se surgir “Salvar alterações?”: perguntar com crop; só prosseguir após resposta
```

---

## 10) Resumo

- **Agora (LLM‑0)**: manter base estável, sem adapters de ação.  
- **Depois (LLM‑1)**: introduzir `app.open`, `file.open_with`, `app.focus`, `app.close` (+ `shell.run` opcional) com **visão contínua** e **confirmação**.  
- **Estilo**: “ver → agir → ver”, pergunta única, evidência mínima, trilho de segurança e aprendizado leve.  
- **Tokens**: deltas curtos, IDs, resumos — cabe folgado em ~8k.
