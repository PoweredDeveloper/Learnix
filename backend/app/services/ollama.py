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


def _normalize_ollama_http_base(url: str) -> str:
    """Ollama.com cloud uses native `/api/chat` on the site root, not OpenAI `/v1/...`."""
    u = url.strip().rstrip("/")
    if u.endswith("/v1"):
        u = u[:-3].rstrip("/")
    return u


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
        mode: str | None = None,
        api_key: str | None = None,
    ) -> None:
        s = get_settings()
        self.base_url = (base_url or s.ollama_base_url).rstrip("/")
        self.model = model or s.ollama_model
        self.timeout_s = timeout_s if timeout_s is not None else s.ollama_timeout_s
        self.mode = mode or s.ollama_mode
        self.api_key = api_key if api_key is not None else s.ollama_api_key

    async def chat_json(self, system: str, user: str) -> dict[str, Any]:
        if self.mode == "cloud":
            return await self._chat_cloud_native(system, user)
        return await self._chat_local_native(system, user)

    def _chat_payload(self, system: str, user: str) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }

    async def _chat_local_native(self, system: str, user: str) -> dict[str, Any]:
        base = _normalize_ollama_http_base(self.base_url)
        payload = self._chat_payload(system, user)
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(f"{base}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
        content = data.get("message", {}).get("content", "")
        return _extract_json_object(content)

    async def _chat_cloud_native(self, system: str, user: str) -> dict[str, Any]:
        """
        Ollama Cloud: same JSON as local `/api/chat`, host `https://ollama.com`, Bearer API key.
        See https://docs.ollama.com/cloud
        """
        key = (self.api_key or "").strip()
        if not key:
            raise ValueError(
                "OLLAMA_API_KEY is required when OLLAMA_MODE=cloud (Ollama.com API key)"
            )
        base = _normalize_ollama_http_base(self.base_url)
        url = f"{base}/api/chat"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        payload = self._chat_payload(system, user)
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            r = await client.post(url, json=payload, headers=headers)
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
            "theory": "Demo theory.",
            "examples": [],
            "topic_title": "Demo",
        }
