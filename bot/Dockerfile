FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
COPY tg_bot ./tg_bot

RUN uv sync --frozen --no-group dev

CMD ["uv", "run", "python", "-m", "tg_bot.main"]
