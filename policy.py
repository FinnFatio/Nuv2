from __future__ import annotations

from typing import List

import metrics


class Policy:
    """Minimal policy implementing simple routing rules."""

    def plan(self, message: str) -> List[str]:
        text = message.lower()

        if any(
            w in text
            for w in ["delete", "remove", "destroy", "format", "shutdown", "rm"]
        ):
            metrics.record_policy_block("destructive")
            return ["forbidden"]
        tools: List[str] = []
        explicit = any(
            v in text
            for v in [
                "faça",
                "faca",
                "use",
                "abra",
                "tira",
                "tirar",
                "take",
                "open",
                "capture",
            ]
        )
        if explicit and "screenshot" in text:
            tools.append("system.capture_screen")
        if explicit and "ocr" in text:
            tools.append("system.ocr")
        if explicit and "zip" in text:
            tools.append("archive.read")
        if any(
            k in text for k in ["price", "preço", "news", "notícia", "weather", "meteo"]
        ):
            tools.append("web.read")
        if any(
            k in text
            for k in [
                "system info",
                "system information",
                "info do sistema",
                "informações do sistema",
                "cpu",
                "ram",
                "gpu",
                "memória",
                "monitor",
                "monitores",
                "safe mode",
            ]
        ):
            tools.append("system.info")

        return tools[:3]
