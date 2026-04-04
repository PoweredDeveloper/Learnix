import pytest


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ensure_and_session_answer(client, api_headers):
    r = await client.post(
        "/users/ensure",
        json={"telegram_id": int(api_headers["X-Telegram-User-Id"]), "name": "Tester", "timezone": "UTC"},
        headers=api_headers,
    )
    assert r.status_code == 200

    r = await client.post("/sessions/start", json={"topic_hint": "Arithmetic"}, headers=api_headers)
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert "2+2" in body["message"] or "Task" in body["message"]

    sid = body["session_id"]
    r2 = await client.post(
        f"/sessions/{sid}/answer",
        json={"text": "4"},
        headers=api_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["correct"] is True

    r3 = await client.post(
        f"/sessions/{sid}/action",
        json={"action": "end"},
        headers=api_headers,
    )
    assert r3.status_code == 200
    assert "summary" in r3.json()


@pytest.mark.asyncio
async def test_streak_endpoint(client, api_headers):
    await client.post(
        "/users/ensure",
        json={"telegram_id": int(api_headers["X-Telegram-User-Id"]), "name": "S", "timezone": "UTC"},
        headers=api_headers,
    )
    r = await client.get("/streak", headers=api_headers)
    assert r.status_code == 200
    data = r.json()
    assert "streak_current" in data
    assert "today_quota_minutes" in data
