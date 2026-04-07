FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

RUN uv sync --frozen --no-group dev

EXPOSE 8000
