# Nuv2

Utilitários de prova de conceito para inspecionar o que está sob o cursor do mouse no Windows.

## Exemplos rápidos

```sh
# Capturar uma região específica
python screenshot.py --region 0,0,100,100 regiao.png
# => salva regiao.png

# Capturar a janela ativa
python screenshot.py --active ativa.png
# => salva ativa.png

# Capturar um monitor específico
python screenshot.py --monitor mon2 mon2.png
# => salva mon2.png

# Emitir JSON junto da captura
python screenshot.py --json --region 0,0,1,1 exemplo.png
# => {"output": "exemplo.png", "region": [0, 0, 1, 1]}

# Exemplo de erro mapeado
python screenshot.py --json --window "janela_que_nao_existe" erro.png
# => {"error": {"code": "window_not_found", "message": "No window matches pattern"}}
```

Para detalhes completos de configuração, uso da CLI e API, consulte [docs/usage.md](docs/usage.md).

### Smoketest LLM

1. Inicie o endpoint de teste:

```sh
python experiments/llm_sandbox/dummy_llm.py
```

2. Em outro terminal, execute os wrappers com o fallback local desabilitado.

**Bash**

```sh
export LLM_ENDPOINT=http://127.0.0.1:8000
export LLM_MODEL=dummy
export LLM_DISABLE_LOCAL_FALLBACK=1
python experiments/llm_sandbox/nu_repl.py <<< "Hello"
```

**PowerShell**

```powershell
$env:LLM_ENDPOINT="http://127.0.0.1:8000"
$env:LLM_MODEL="dummy"
$env:LLM_DISABLE_LOCAL_FALLBACK="1"
python experiments/llm_sandbox/run_llm_eval_llamacpp.py
```

<a id="log-config"></a>
## Configurações de log

| Variável | Descrição | Exemplo |
|---------|-----------|---------|
| `LOG_FORMAT` | formato dos logs (`text` ou `json`) | `json` |
| `LOG_LEVEL` | nível mínimo de log (`debug`, `info`, `warning`, `error`, `critical`) | `debug` |
| `LOG_RATE_LIMIT_HZ` | limite de frequência de logs por segundo | `2` |

## Módulos

- `cursor.py`: posição atual do cursor.
- `screenshot.py`: capturar regiões da tela.
- `uia.py`: consultar UI Automation para propriedades de elementos.
- `ocr.py`: extrair texto via OCR.
- `resolve.py`: combinar UIA e OCR com heurísticas de confiança.
- `what_is_under_mouse.py`: CLI simples que exibe descrição em JSON.
- `hover_watch.py`: descreve repetidamente o que está sob o cursor.
- `inspect_point.py`: descreve um ponto dado sem mover o cursor.

## Dependências

As bibliotecas necessárias estão listadas em `requirements.txt`. Instale-as com:

```sh
pip install -r requirements.txt
```

Principais dependências:

- `mss` para captura de tela.
- `Pillow` para manipulação de imagens.
- `pytesseract` para OCR.
- `psutil` para informações de processos.
- `fastapi` para o servidor HTTP.
- `pygetwindow` (opcional) para manipulação de janelas.
- `llama-cpp-python` (opcional) para fallback local da LLM – CPU: `pip install llama-cpp-python`; AMD ROCm: instale sua build local; NVIDIA/CUDA: wheel específico.

## Desenvolvimento

Para configurar o ambiente de desenvolvimento e executar as validações locais:

```sh
pip install -r requirements.txt
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

As verificações incluem formatação e lint com `ruff`, tipos estritos com `mypy` para
`cli_helpers.py`, `logger.py` e `settings.py`, além de testes com `pytest -q`.

## Links principais (raw)

### Documentação
- [Milestone](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/Milestone.md)
- [README](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/README.md)
- [Changelog](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/chatgpt.md)

### Núcleo
- [api.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/api.py)
- [resolve.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/resolve.py)
- [screenshot.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/screenshot.py)
- [ocr.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/ocr.py)
- [primitives.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/primitives.py)

### Utilitários
- [cli_helpers.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/cli_helpers.py)
- [cursor.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/cursor.py)
- [hover_watch.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/hover_watch.py)
- [inspect_point.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/inspect_point.py)

### Infra/Config
- [logger.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/logger.py)
- [metrics.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/metrics.py)
- [mypy.ini](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/mypy.ini)
- [requirements.txt](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/requirements.txt)
- [settings.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/settings.py)

### Outros
- [uia.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/uia.py)
- [what_is_under_mouse.py](https://raw.githubusercontent.com/FinnFatio/Nuv2/main/what_is_under_mouse.py)
