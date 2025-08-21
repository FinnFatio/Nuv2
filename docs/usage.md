# Uso

## Configuração

Opções podem ser fornecidas via variáveis de ambiente, arquivo `.env` ou arquivo `config.json` no diretório do projeto. Variáveis de ambiente têm precedência sobre `.env`, que por sua vez substitui `config.json`.

- `OCR_LANG` – idiomas para o Tesseract (padrão: `por+eng`)
- `OCR_CFG` – string de configuração extra para o Tesseract (padrão: `--oem 3 --psm 6`)
- `CAPTURE_WIDTH` – largura da região de captura (padrão: `300`)
- `CAPTURE_HEIGHT` – altura da região de captura (padrão: `120`)
- `UIA_THRESHOLD` – limiar da heurística de texto da UIA (padrão: `4.0`)
- `TESSERACT_CMD` – caminho para o executável do Tesseract, caso não esteja no `PATH`
- `CAPTURE_LOG_SAMPLE_RATE` – proporção de capturas que geram log (padrão: `0.1`)
- `CAPTURE_LOG_DEST` – destino dos logs de captura (`stderr` ou `file:caminho`)
- `LOG_LEVEL` – nível global de log (`debug`, `info`, `warning`; padrão: `info`)
- `LOG_FORMAT` – formato dos logs (`text` ou `json`; padrão: `text`)
- `LOG_RATE_LIMIT_HZ` – limite de frequência dos logs por segundo (padrão: desativado)

Consulte a [tabela de configurações de log](../README.md#log-config) para exemplos de
`LOG_FORMAT`, `LOG_LEVEL` e `LOG_RATE_LIMIT_HZ`.

Quando `LOG_LEVEL=debug`, um digest de configuração e versão é emitido no início da execução.

Exemplo de diferença entre formatos de log:

```
INFO: hello
```

```
{"level": "INFO", "message": "hello"}
```

Exemplo de customização do logger:

```sh
CAPTURE_LOG_DEST=file:capturas.log LOG_LEVEL=debug LOG_FORMAT=json python hover_watch.py --hz 2
```


## Exemplos de saída

Evento de captura em formato de texto:

```
INFO: capture region=0,0,100,100 path=out.png
```

Mesmo evento em formato JSON:

```json
{"level": "INFO", "event": "capture", "region": [0,0,100,100], "path": "out.png"}
```

Exemplo de erro na CLI:

```sh
python screenshot.py --json --region 0,0,-1,1 out.png
# => {"error": {"code": "bad_region", "message": "Invalid capture region (0,0,-1,1)"}}
```

## CLI

```sh
python what_is_under_mouse.py
```

O comando imprime um objeto JSON com a localização do cursor, aplicação e elemento, texto detectado e escores de confiança.

Vigilância contínua:

```sh
python hover_watch.py --hz 2
```

Capturar uma imagem:

```sh
python screenshot.py --region 0,0,800,600 exemplo.png
```

Capturar um monitor específico:

```sh
python screenshot.py --monitor mon2 monitor.png
```

Aplicar timeout na busca de janela:

```sh
python screenshot.py --window bloco --timeout 0.5 out.png
```

As ferramentas de CLI e API retornam erros no formato:

```json
{"error": {"code": "...", "message": "..."}}
```

Exemplo de erro mapeado:

```sh
python screenshot.py --json --window janela_inexistente out.png
# => {"error": {"code": "window_not_found", "message": "No window matches pattern"}}

```

### Formato de saída

Quando `--json` é utilizado, a CLI emite exatamente uma linha de JSON na
`stdout`:

```sh
python screenshot.py --json --region 0,0,1,1 out.png
# => {"output":"out.png","region":[0,0,1,1]}
```

Sem região explícita, o campo `region` será `null`:

```sh
python screenshot.py --json out.png
# => {"output":"out.png","region":null}
```

Em caso de erro, o JSON contém um objeto `error`:

```sh
python screenshot.py --json --region 0,0,-1,1 out.png
# => {"error":{"code":"bad_region","message":"Invalid capture region (0,0,-1,1)"}}
```

### Códigos de saída

- `0` – sucesso
- `1` – erro operacional (ex.: `window_not_found`)
- `2` – região inválida

### Códigos de erro da CLI

| Código               | Descrição exemplo                      |
|----------------------|----------------------------------------|
| `bad_region`         | Região inválida na CLI                 |
| `pygetwindow_missing`| pygetwindow ausente para captura       |
| `no_active_window`   | Nenhuma janela ativa                   |
| `window_not_found`   | Nenhuma janela corresponde ao padrão   |
| `window_search_timeout` | Busca de janela demorou demais      |
| `tesseract_missing`  | Binário do Tesseract ausente           |
| `tesseract_failed`   | Erro ao executar Tesseract             |
| `capture_failed`     | Falha inesperada na captura            |

### Instalação do Tesseract

O OCR depende do [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract). No Windows, baixe o instalador em
<https://github.com/UB-Mannheim/tesseract/wiki> ou instale via Chocolatey:

```sh
choco install tesseract
```

Após a instalação, se o binário não estiver no `PATH`, defina `TESSERACT_CMD` apontando para o executável:

```sh
setx TESSERACT_CMD "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
```

### Saúde da captura

Para diagnósticos rápidos, `screenshot.health_check()` retorna os limites atuais da
tela e a latência aproximada de captura.

Inspecionar um ponto específico:

```sh
python inspect_point.py --point 100,200
```

## API

Execute um pequeno servidor HTTP com FastAPI:

```sh
uvicorn api:app --port 8000
```

### Runtime HTTP

Após iniciar o servidor, os seguintes endpoints estão disponíveis:

- `GET /inspect?x=&y=` – JSON do alvo.
- `GET /details?id=` – metadados e affordances.
- `GET /snapshot?id=ID` ou `GET /snapshot?region=x,y,w,h` – imagem PNG.
- `GET /metrics` – métricas agregadas de latência, fallbacks e erros.

Um ciclo típico de automação é **observe → plan → act → verify**:

1. **Observe** com `GET /inspect` ou `GET /details`.
2. **Plan** a ação com base na resposta.
3. **Act** será suportado futuramente via `POST /act`.
4. **Verify** chamando novamente `GET /inspect` para confirmar o resultado.

As respostas e logs seguem a mesma estrutura JSON das ferramentas de linha de comando.

### Códigos de erro

| Código              | Descrição exemplo                      |
|---------------------|----------------------------------------|
| `id_not_found`      | ID não encontrado                       |
| `missing_id_or_region` | Parâmetros `id` ou `region` ausentes |
| `invalid_region`    | Região inválida                         |
| `region_too_large`  | Região excede limite                    |
| `pygetwindow_missing` | pygetwindow ausente para captura       |
| `no_active_window`  | Nenhuma janela ativa                    |
| `window_not_found`  | Nenhuma janela corresponde ao padrão    |
| `window_search_timeout` | Busca de janela demorou demais      |
| `rate_limit`        | Limite de requisições excedido          |
| `bad_region`        | Região inválida na CLI                  |
| `tesseract_missing` | Binário do Tesseract ausente            |
| `tesseract_failed`  | Erro ao executar Tesseract              |
| `capture_failed`    | Falha inesperada na captura             |

## Próximos Passos

Pretende-se disponibilizar um endpoint `POST /act` que permita simular ações antes de executá-las, reforçando a segurança e a validação das interações automatizadas. Essa camada de simulação garante que apenas comandos aprovados sejam aplicados ao sistema real. A documentação será expandida assim que o endpoint estiver disponível.

