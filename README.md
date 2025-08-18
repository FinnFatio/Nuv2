# Nuv2

Proof-of-concept utilities to inspect what is under the mouse cursor on Windows.

## Modules

- `cursor.py`: current cursor position.
- `screenshot.py`: capture screen regions.
- `uia.py`: query UI Automation for element properties.
- `ocr.py`: extract text via OCR.
- `resolve.py`: combine UIA and OCR with confidence heuristics.
- `what_is_under_mouse.py`: simple CLI outputting JSON description.

## Dependencies

- `mss` for screen capturing.

## Usage

```sh
python what_is_under_mouse.py
```

The command prints a JSON object with the cursor location, application and element
information, detected text and confidence scores.
