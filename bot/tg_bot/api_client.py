from typing import Any
from uuid import UUID

import httpx


class BackendClient:
    def __init__(self, base_url: str, api_secret: str, telegram_user_id: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.telegram_user_id = telegram_user_id
        self.headers = {
            "X-API-Key": api_secret,
            "X-Telegram-User-Id": str(telegram_user_id),
        }

    async def ensure_user(self, name: str | None, timezone: str = "UTC") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{self.base_url}/users/ensure",
                json={"telegram_id": self.telegram_user_id, "name": name, "timezone": timezone},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def tasks_today(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(f"{self.base_url}/tasks/today", headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def streak(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(f"{self.base_url}/streak", headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def session_start(self, topic_hint: str | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{self.base_url}/sessions/start",
                json={"topic_hint": topic_hint},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def session_answer(self, session_id: UUID, text: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{self.base_url}/sessions/{session_id}/answer",
                json={"text": text},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def session_action(self, session_id: UUID, action: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{self.base_url}/sessions/{session_id}/action",
                json={"action": action},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def update_task(self, task_id: UUID, status: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.patch(
                f"{self.base_url}/tasks/{task_id}",
                json={"status": status},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()
