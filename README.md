# Nuv2

Proof-of-concept utilities to inspect what is under the mouse cursor on Windows.

## Modules

- `cursor.py`: current cursor position.
- `screenshot.py`: capture screen regions.
- `uia.py`: query UI Automation for element properties.
- `ocr.py`: extract text via OCR.
- `resolve.py`: combine UIA and OCR with confidence heuristics.
- `what_is_under_mouse.py`: simple CLI outputting JSON description.
- `hover_watch.py`: repeatedly describe what's under the cursor.
- `inspect.py`: describe a given point without moving the cursor.

## Dependencies

- `mss` for screen capturing.

## Configuration

Options can be provided via environment variables, a `.env` file or a
`config.json` file in the project directory. Environment variables have
precedence over `.env`, which in turn override `config.json`.

- `OCR_LANG` – languages for Tesseract (default: `por+eng`)
- `OCR_CFG` – extra Tesseract config string (default: `--oem 3 --psm 6`)
- `CAPTURE_WIDTH` – width of the screenshot region (default: `300`)
- `CAPTURE_HEIGHT` – height of the screenshot region (default: `120`)
- `UIA_THRESHOLD` – confidence threshold for preferring UIA text (default: `0.7`)

## Usage

```sh
python what_is_under_mouse.py
```

The command prints a JSON object with the cursor location, application and element
information, detected text and confidence scores.

Continuous watch:

```sh
python hover_watch.py --hz 2
```

Capture a screenshot:

```sh
python screenshot.py --region 0,0,800,600 example.png
```

Inspect a specific point:

```sh
python inspect.py --point 100,200
```
