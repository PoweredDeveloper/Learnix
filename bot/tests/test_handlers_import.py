def test_backend_client_headers():
    from tg_bot.api_client import BackendClient

    c = BackendClient("http://x", "secret", 42)
    assert c.headers["X-Telegram-User-Id"] == "42"
    assert c.headers["X-API-Key"] == "secret"
