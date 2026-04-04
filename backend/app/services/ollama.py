import json
import re
from typing import Any

import httpx

from app.core.config import get_settings


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object in model response")
    return json.loads(m.group())


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
    ) -> None:
        s = get_settings()
        self.base_url = (base_url or s.ollama_base_url).rstrip("/")
        self.model = model or s.ollama_model
        self.timeout_s = timeout_s if timeout_s is not None else s.ollama_timeout_s

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
        content = data.get("message", {}).get("content", "")
        return _extract_json_object(content)


class MockOllamaClient:
    """Test double: set `response_queue` with dicts to return in order."""

    def __init__(self) -> None:
        self.response_queue: list[dict[str, Any]] = []

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        if self.response_queue:
            return self.response_queue.pop(0)
        return {
            "explanation": "Demo explanation.",
            "task": "What is 2+2?",
            "rubric": "Answer should be 4.",
        }
