import pytest

from app.services.ollama import OllamaClient


@pytest.mark.asyncio
async def test_cloud_mode_requires_api_key():
    client = OllamaClient(
        base_url="https://ollama.com/v1",
        model="llama3.2",
        timeout_s=1.0,
        mode="cloud",
        api_key="",
    )
    with pytest.raises(ValueError, match="OLLAMA_API_KEY"):
        await client.chat_json("sys", "user")
