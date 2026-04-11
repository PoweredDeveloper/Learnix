import asyncio
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

    async def get_me(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(f"{self.base_url}/users/me", headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def ensure_web_session(self) -> dict[str, Any]:
        last: BaseException | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    r = await client.post(
                        f"{self.base_url}/users/me/web-session",
                        headers=self.headers,
                    )
                    r.raise_for_status()
                    return r.json()
            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ) as e:
                last = e
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2**attempt))
        assert last is not None
        raise last

    async def complete_onboarding(self, answers: dict[str, str]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{self.base_url}/users/me/onboarding",
                json={"answers": answers},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def create_course_theme(self, theme: str, days: int = 14) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{self.base_url}/courses/personalized-theme",
                json={"theme": theme, "days": days},
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def create_course_file(
        self,
        filename: str,
        content: bytes,
        days: int = 14,
        subject_name: str | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=180.0) as client:
            files = {"file": (filename, content)}
            data: dict[str, str] = {"days": str(days)}
            if subject_name:
                data["subject_name"] = subject_name
            r = await client.post(
                f"{self.base_url}/courses/personalized-file",
                files=files,
                data=data,
                headers={k: v for k, v in self.headers.items()},
            )
            r.raise_for_status()
            return r.json()

    async def ensure_user(self, name: str | None, timezone: str = "UTC") -> dict[str, Any]:
        """POST /users/ensure with retries on transient Docker / network blips."""
        last: BaseException | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post(
                        f"{self.base_url}/users/ensure",
                        json={
                            "telegram_id": self.telegram_user_id,
                            "name": name,
                            "timezone": timezone,
                        },
                        headers=self.headers,
                    )
                    r.raise_for_status()
                    return r.json()
            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ) as e:
                last = e
                if attempt < 2:
                    await asyncio.sleep(0.6 * (2**attempt))
        assert last is not None
        raise last

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

    async def list_subjects(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(f"{self.base_url}/subjects", headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def session_start(
        self,
        topic_hint: str | None = None,
        subject_id: UUID | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if topic_hint is not None:
            body["topic_hint"] = topic_hint
        if subject_id is not None:
            body["subject_id"] = str(subject_id)
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{self.base_url}/sessions/start",
                json=body,
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
