# Smart Study Assistant (SETHack)

Telegram-first study planner with **FastAPI** + **PostgreSQL**, **aiogram** bot, **React** dashboard, and **Ollama** for AI features. See `PLAN.md` and `AGENT.md` for product scope and agent rules.

## Quick start

1. **Database & API**

   Install [uv](https://docs.astral.sh/uv/). Then:

   ```bash
   docker compose up -d db
   cd backend
   uv sync --group dev
   cp ../.env.example ../.env   # optional; defaults match compose
   export DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/sethack
   uv run alembic upgrade head
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Postgres is exposed on **host port 5433** (see `docker-compose.yml`).

2. **Ollama**
   - **Local:** run `ollama serve` on the host and pull a model, e.g. `ollama pull llama3.2`. Use `OLLAMA_MODE=local` and `OLLAMA_BASE_URL=http://127.0.0.1:11434` (Docker API service uses `host.docker.internal:11434` by default).
   - **Cloud:** set `OLLAMA_MODE=cloud`, `OLLAMA_BASE_URL=https://ollama.com`, and `OLLAMA_API_KEY` from [ollama.com/settings/keys](https://ollama.com/settings/keys). Uses the same `/api/chat` JSON as local ([docs](https://docs.ollama.com/cloud)). Pick a **cloud** model (e.g. `gpt-oss:120b`). If the base URL is still the default localhost, the app defaults to `https://ollama.com`. A trailing `/v1` in the URL is stripped automatically.

3. **Bot**

   ```bash
   cd bot
   uv sync --group dev
   export TELEGRAM_BOT_TOKEN=... API_BASE_URL=http://127.0.0.1:8000 API_SECRET=dev-secret-change-me
   uv run python -m tg_bot.main
   ```

4. **Web**

   ```bash
   cd web && npm install && npm run dev
   ```

   Open http://localhost:5173 — set your Telegram numeric ID to match the bot user. Vite proxies `/api` → `http://127.0.0.1:8000`.

## Docker

**`docker compose up -d --build`** starts **db**, **api**, **web**, and **bot**.

| Service  | Host port | Notes                                                                                                                    |
| -------- | --------- | ------------------------------------------------------------------------------------------------------------------------ |
| Postgres | **5433**  | —                                                                                                                        |
| API      | **8000**  | OpenAPI at `/docs`                                                                                                       |
| Web      | **5173**  | Caddy serves the built React app; `/api/*` is proxied to the API                                                         |
| Bot      | —         | Requires **`TELEGRAM_BOT_TOKEN`** in project `.env`; if it is missing, the bot container exits (set it from @BotFather). |

The bot’s **`WEB_PUBLIC_BASE_URL`** defaults to **`http://localhost:5173`** in Compose (same host port as **web**), so the menu **Web app** link works for Telegram Desktop on the same machine. Override with an **HTTPS** URL (e.g. ngrok) for Telegram on a phone, and add that origin to **`CORS_ORIGINS`**.

Set **`API_SECRET`** and **`VITE_API_SECRET`** to the same value in `.env` so the web UI’s `X-API-Key` matches the API (or rebuild `web` after changing `VITE_API_SECRET`).

For **local development** without Docker, use `cd web && npm run dev` instead of the `web` service.

Ensure Ollama is reachable from the API container when using local mode (`OLLAMA_BASE_URL`); on Mac, `host.docker.internal:11434` is the default in compose.

## Tests

```bash
# Backend (needs Postgres test DB on 5433 — created by docker/postgres-init.sql)
cd backend && uv sync --group dev && uv run pytest
```

```bash
cd bot && uv sync --group dev && uv run pytest
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

Optional **`LMS_BACKEND_API_KEY`** (see `.env.example`) is loaded into backend settings for future LMS integration; set it in `.env` when you wire outbound LMS calls.
