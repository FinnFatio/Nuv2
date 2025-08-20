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

