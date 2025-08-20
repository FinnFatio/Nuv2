# Nuv2

Utilitários de prova de conceito para inspecionar o que está sob o cursor do mouse no Windows.

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

## Configuração

Opções podem ser fornecidas via variáveis de ambiente, arquivo `.env` ou arquivo `config.json` no diretório do projeto. Variáveis de ambiente têm precedência sobre `.env`, que por sua vez substitui `config.json`.

- `OCR_LANG` – idiomas para o Tesseract (padrão: `por+eng`)
- `OCR_CFG` – string de configuração extra para o Tesseract (padrão: `--oem 3 --psm 6`)
- `CAPTURE_WIDTH` – largura da região de captura (padrão: `300`)
- `CAPTURE_HEIGHT` – altura da região de captura (padrão: `120`)
- `UIA_THRESHOLD` – limiar de confiança para preferir texto de UIA (padrão: `0.7`)
- `TESSERACT_CMD` – caminho para o executável do Tesseract, caso não esteja no `PATH`

## Exemplos rápidos

```sh
# Capturar uma região específica
python screenshot.py --region 0,0,100,100 regiao.png
# => salva regiao.png

# Capturar a janela ativa
python screenshot.py --active ativa.png
# => salva ativa.png

# Emitir JSON junto da captura
python screenshot.py --json --region 0,0,1,1 exemplo.png
# => {"output": "exemplo.png", "region": [0, 0, 1, 1]}
```

## Uso

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

Inspecionar um ponto específico:

```sh
python inspect_point.py --point 100,200
```

## API

Execute um pequeno servidor HTTP com FastAPI:

```sh
uvicorn api:app --port 8000
```

## Runtime HTTP

Após iniciar o servidor, os seguintes endpoints estão disponíveis:

- `GET /inspect?x=&y=` – JSON do alvo.
- `GET /details?id=` – metadados e affordances.
- `GET /snapshot?id=ID` ou `GET /snapshot?region=x,y,w,h` – imagem PNG.

Um ciclo típico de automação é **observe → plan → act → verify**:

1. **Observe** com `GET /inspect` ou `GET /details`.
2. **Plan** a ação com base na resposta.
3. **Act** será suportado futuramente via `POST /act`.
4. **Verify** chamando novamente `GET /inspect` para confirmar o resultado.

As respostas e logs seguem a mesma estrutura JSON das ferramentas de linha de comando.

## Próximos Passos

Pretende-se disponibilizar um endpoint `POST /act` que permita simular ações antes de executá-las, reforçando a segurança e a validação das interações automatizadas.
Essa camada de simulação garante que apenas comandos aprovados sejam aplicados ao sistema real.

A documentação será expandida assim que o endpoint estiver disponível.
