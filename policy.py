from __future__ import annotations

from typing import List


class Policy:
    """Very small policy stub used for tests."""

    def plan(self, message: str) -> List[str]:
        if "screenshot" in message:
            return ["system.capture_screen"]
        if "ocr" in message:
            return ["system.ocr"]
        return []
