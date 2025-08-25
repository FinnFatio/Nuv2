from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.post("/v1/chat/completions")
async def chat(payload: Dict[str, Any]) -> JSONResponse:  # type: ignore[override]
    messages = payload.get("messages", [])
    content = "dummy response"
    if messages:
        last = str(messages[-1].get("content", ""))
        if "tool" in last.lower():
            content = '<toolcall>{"name":"system.info","args":{}}</toolcall>'
    data = {"choices": [{"message": {"content": content}}], "usage": {}}
    return JSONResponse(content=data, media_type="application/json")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
