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
