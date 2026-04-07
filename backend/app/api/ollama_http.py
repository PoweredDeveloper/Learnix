import httpx
from fastapi import HTTPException, status


def raise_for_ollama_http(exc: BaseException) -> None:
    """Map httpx errors from Ollama into HTTP 502 for API clients."""
    if isinstance(exc, httpx.HTTPStatusError):
        text = (exc.response.text or "")[:500].strip() or exc.response.reason_phrase
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ollama HTTP {exc.response.status_code}: {text}",
        ) from exc
    if isinstance(exc, httpx.RequestError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ollama unreachable: {exc}",
        ) from exc
    raise exc
