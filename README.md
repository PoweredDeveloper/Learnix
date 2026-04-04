# Smart Study Assistant (SETHack)

Telegram-first study planner with **FastAPI** + **PostgreSQL**, **aiogram** bot, **React** dashboard, and **Ollama** for AI features. See `PLAN.md` and `AGENT.md` for product scope and agent rules.

## Quick start

1. **Database & API**

   ```bash
   docker compose up -d db
   cd backend
   python3 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   cp ../.env.example ../.env   # optional; defaults match compose
   export DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/sethack
   alembic upgrade head
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Postgres is exposed on **host port 5433** (see `docker-compose.yml`).

2. **Ollama** (host): run `ollama serve` and pull a model, e.g. `ollama pull llama3.2`.

3. **Bot**

   ```bash
   cd bot
   python3 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   export TELEGRAM_BOT_TOKEN=... API_BASE_URL=http://127.0.0.1:8000 API_SECRET=dev-secret-change-me
   python -m tg_bot.main
   ```

4. **Web**

   ```bash
   cd web && npm install && npm run dev
   ```

   Open http://localhost:5173 — set your Telegram numeric ID to match the bot user. Vite proxies `/api` → `http://127.0.0.1:8000`.

## Docker (API only)

```bash
docker compose up --build api
```

Ensure Ollama is reachable from the API container (`OLLAMA_BASE_URL`); on Mac, `host.docker.internal:11434` is set in compose.

## Tests

```bash
# Backend (needs Postgres test DB on 5433 — created by docker/postgres-init.sql)
cd backend && source .venv/bin/activate
pytest
```

```bash
cd web && npx playwright install && npm run test:e2e
```

(API must be up for streak/tasks calls from the web app; smoke test only checks the page shell.)

## Auth (MVP)

All protected API routes require:

- `X-API-Key: <API_SECRET>`
- `X-Telegram-User-Id: <telegram numeric id>`

The bot and web send these on every request.
