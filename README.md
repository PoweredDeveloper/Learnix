# Learnix

[![CI](https://github.com/PoweredDeveloper/Learnix/actions/workflows/ci.yml/badge.svg)](https://github.com/PoweredDeveloper/Learnix/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![aiogram](https://img.shields.io/badge/aiogram-Telegram-26A5E4?style=flat&logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![Ollama](https://img.shields.io/badge/Ollama-LLM-111111?style=flat)](https://ollama.com/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?style=flat&logo=ubuntu&logoColor=white)](https://ubuntu.com/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=flat&logo=github)](https://github.com/PoweredDeveloper/Learnix)

![Dashboard](img/img1.png)

Telegram-first smart study assistant: AI-generated courses, a web dashboard, and a bot for plans, reminders, and guided practice—backed by FastAPI, PostgreSQL, React, and Ollama.

## Lesson page

![Lesson / learning UI](img/img2.png)

## Product context

**End users**  
Students and self-learners who already use **Telegram** daily and want structure without juggling separate “chat with AI” tabs that forget their syllabus the next day.

**Problem**  
Generic chatbots do not persist a real **course structure** (sections, lessons, tasks), do not turn uploads into durable **study material**, and do not tie progress to **habits** (streaks, reminders) in the same place students already check messages.

**Solution**  
**Learnix** keeps **courses and lessons** in a database, uses **Ollama** to generate syllabi and lesson content from a topic (and optional reference text), exposes a **React** web app for deep reading and exercises, and uses an **aiogram** bot for **daily nudges**, quick links to the web app, and a consistent **API-key + Telegram user ID** identity model.

## Features

### Implemented

- **Courses & lessons:** Create courses (topic, duration, optional file text); AI builds a syllabus and per-lesson content (theory, practice, exam-style questions).
- **Web dashboard:** Progress overview, metrics (streak, lessons, study time), course list, course detail with lesson navigation.
- **Lesson experience:** Markdown + LaTeX rendering, practice tasks with AI grading (JSON), exam sections, side AI tutor chat, “complete lesson” flow.
- **Study time & streaks:** Minutes counted toward daily goals when lessons are completed (and related streak logic on the backend).
- **Telegram bot:** Menu, web-app links, integration with the same backend as the web UI.
- **Notifications:** User timezone, daily reminder time, and optional dated reminders (stored in the API; bot dispatch uses internal endpoints).
- **Deployment:** `docker compose` stack: Postgres, API, static web (Caddy), bot; optional **Ollama** on the host or **Ollama Cloud** via env vars.
- **Auth (MVP):** Protected routes require `X-API-Key` and `X-Telegram-User-Id` (bot and web send these after session bootstrap).

### Not yet implemented (roadmap)

- **Multiple languages:** UI and lesson content localization (i18n), plus model prompts tuned per locale.
- **Spaced repetition:** Export or built-in decks (e.g. Anki) from lesson highlights and wrong answers.
- **Rich LMS integration:** Deep link-out to Canvas/Moodle with grade sync (settings mention future LMS API key).
- **Native mobile apps:** Dedicated iOS/Android clients beyond Telegram WebApp and the browser.
- **Collaborative study:** Shared courses, study groups, and peer progress visibility.
- **Offline mode:** Download lessons for offline reading without network.
- **Accessibility extras:** Screen-reader-first lesson layouts, optional TTS for lesson body text.

## Usage

1. **Get access via Telegram**  
   Use the project’s bot (token configured by operators). Open the **Web app** link from the bot menu or the flow your deployment documents so the browser receives a valid web session (the UI expects the Telegram-linked flow).

2. **Web dashboard**  
   Open the deployed web URL (e.g. `https://your-host/`). You should see courses, streaks, and “Study today” style metrics. Create a **new course** from the dashboard; wait for generation to finish if the course status shows generating.

3. **Study a course**  
   Open a course, pick a lesson from the sidebar. Read the material, use the **AI chat** for questions, complete **practice** (submit answers for grading), finish **exam** items if present, then use **Complete & continue** when the UI allows.

4. **Settings**  
   Set **timezone** and **daily reminder** (and optional one-off reminders) so Telegram messages fire at the correct local time.

5. **API**  
   Operators can inspect OpenAPI at `http://<api-host>:8000/docs` when the API is exposed (development or VPN-only in production).

**Local development (no full Docker stack for web):** from `web/`, `npm install && npm run dev` with Vite proxying `/api` to the API (see `.env.example` for `VITE_API_SECRET` alignment with `API_SECRET`).

## Deployment

Assume a fresh **Ubuntu 24.04 LTS** VM (same family as typical university lab images).

### What to install on the VM

- **Git** — clone the repository.
- **Docker Engine** and the **Docker Compose plugin** — run the stack (`docker compose`).
- **Optional but common for local LLM:** **Ollama** on the VM host (or use **Ollama Cloud** and skip a large local model).

You do _not_ need to install Python or Node on the host if you only run services via Docker images built from this repo (the API and web Dockerfiles bundle runtimes). Install `uv` only if you run the API or bot directly on the host for debugging.

### Step-by-step deployment

1. **SSH into the VM** and update packages:

   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Docker** (official Docker docs for Ubuntu 24.04), then ensure your user can run Docker:

   ```bash
   sudo usermod -aG docker "$USER"
   # log out and back in for group membership
   ```

3. **Clone the repository:**

   ```bash
   git clone <your-repo-url> learnix && cd learnix
   ```

4. **Configure environment**  
   Copy `.env.example` to `.env` at the repo root and set at minimum:
   - `API_SECRET` — shared secret for the API.
   - `VITE_API_SECRET` — **same value** as `API_SECRET` before building the web image (it is baked in at build time).
   - `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather); required for the **bot** container to stay up.
   - `WEB_PUBLIC_BASE_URL` — public **HTTPS** URL of the web app (e.g. `https://learnix.example.edu`) so Telegram clients can open the WebApp; add that origin to `CORS_ORIGINS` for the API.
   - **Ollama:** either run Ollama on the VM and set `OLLAMA_MODE=local` and `OLLAMA_BASE_URL` (from inside Docker, the host is often `http://172.17.0.1:11434` on Linux, or publish Ollama on a host port and point the URL there), **or** set `OLLAMA_MODE=cloud`, `OLLAMA_BASE_URL=https://ollama.com`, and `OLLAMA_API_KEY`.

5. **Ollama on the same VM (typical local setup)**  
   Install Ollama, `ollama serve`, and `ollama pull <OLLAMA_MODEL>`. Ensure the API container can reach that address (`OLLAMA_BASE_URL` in `.env`).

6. **Build and start the stack:**

   ```bash
   docker compose up -d --build
   ```

   If Compose reports a **container name already in use** (for example `learnix-api-1`), remove the orphan and retry: `docker rm -f learnix-api-1`, or run `docker compose down --remove-orphans` from this repo, then `docker compose up -d` again. The stack uses project name **`learnix`** and fixed names such as **`learnix-api`** and **`learnix-web`** to avoid stray `*-1` containers when the project path changes.

   Services (see `docker-compose.yml`):

   | Service  | Host port | Notes                                                    |
   | -------- | --------- | -------------------------------------------------------- |
   | Postgres | **5433**  | Database (init script under `docker/`).                  |
   | API      | **8000**  | FastAPI; health at `/health`.                            |
   | Web      | **5173**  | Caddy serves the built SPA; proxies `/api/*` to the API. |
   | Mihomo   | —         | Telegram HTTP proxy on **7890** (DIRECT unless subscription set). |
   | Bot      | —         | Needs `TELEGRAM_BOT_TOKEN`; optional `TELEGRAM_HTTP_PROXY` via Mihomo when egress is blocked. |

7. **TLS and reverse proxy (production)**  
   Put **Caddy** or **nginx** with Let’s Encrypt in front of ports **5173** (web) and optionally **8000** (API) if you expose the API publicly; restrict `/docs` if needed.

   **nginx-proxy (external `proxy-net`):** If the reverse proxy runs in another Compose project, attach the web container to the same user-defined network or nginx-proxy will return **502**. From the repo root:

   ```bash
   docker network create proxy-net   # once, if it does not exist yet
   docker compose -f docker-compose.yml -f Learnix/docker-compose.yml up -d --build
   ```

   That merge sets `container_name: learnix-web` and joins **`proxy-net`** (see `Learnix/docker-compose.yml`). For large uploads and long AI streams through nginx-proxy, copy `Learnix/nginx-proxy-vhost.d.example.conf` into your `vhost.d/<hostname>` snippet (body size and proxy read/send timeouts). The in-stack **Caddy** front for `/api` also disables response buffering and extends read/write timeouts for streaming.

8. **Migrations**  
   The API container runs `alembic upgrade head` on startup. For a fresh database, ensure Postgres is healthy before the API starts (`depends_on` handles ordering in Compose).

9. **Firewall**  
   Allow **443** (and **80** for ACME) for the web app; expose **8000** only on an admin network if you do not want a public API.

### Database volumes

If an old **`pgdata`** volume was created before `docker/postgres-init.sql` ran, the **`sethack_test`** database (or even **`sethack`**) may be missing and the API will fail migrations. Run `./docker/ensure-databases.sh` from the host against the published port (defaults: `PGHOST=127.0.0.1` `PGPORT=5433`), or pipe the script into `docker compose exec -T db …` as documented in the script header. Set **`ENSURE_POSTGRES_PASSWORD=1`** once if the superuser password no longer matches `postgres` in compose.

### Telegram egress (Mihomo sidecar)

**Mihomo** is part of the default `docker compose` stack. The bot talks to **Telegram directly** by default (no `TELEGRAM_HTTP_PROXY`). Set **`TELEGRAM_HTTP_PROXY=http://mihomo:7890`** in `.env` only when outbound access to **api.telegram.org** must go through Mihomo (e.g. you use **`PROXY_SUBSCRIPTION_*`** on the mihomo service). Forcing the bot through Mihomo in **DIRECT** mode (no subscription) can break **aiogram**’s HTTPS session on some setups, so avoid that unless you have a real upstream.

- **No subscription:** Mihomo still runs in **DIRECT** passthrough on **7890** for optional use; the bot does not need it unless you configure a proxy as above.
- **With subscription:** set **`PROXY_SUBSCRIPTION_URL`**, **`PROXY_SUBSCRIPTION_FILE`**, or **`PROXY_SUBSCRIPTION_RAW`** for `mihomo`, then set **`TELEGRAM_HTTP_PROXY=http://mihomo:7890`** on the bot.

**`aiohttp-socks`** is only needed for **socks5://** proxies on the bot; it is listed in `bot/pyproject.toml`.

### Ollama notes

- **Docker API + Ollama on VM:** On Linux, `host.docker.internal` may be unavailable unless configured; prefer the host gateway IP or publish `11434` and use `http://<vm-ip>:11434` from compose via `OLLAMA_BASE_URL`.
- **Cloud mode:** No large model RAM on the VM; you need a valid Ollama.com API key and a cloud-capable model name.

## Tests

```bash
# Backend (Postgres test DB on 5433 — see docker/postgres-init.sql)
cd backend && uv sync --group dev && uv run pytest
```

```bash
cd bot && uv sync --group dev && uv run pytest
```

```bash
cd web && npx playwright install && npm run test:e2e
```

## Further reading

- `PLAN.md` — product scope and architecture notes.
- `AGENT.md` — agent / automation guidelines for this repo.
- `.env.example` — full list of environment variables.
- `Learnix/docker-compose.yml` — production merge overlay for **nginx-proxy** / **`proxy-net`**.
- `docker/ensure-databases.sh` — ensure **`sethack`** / **`sethack_test`** exist on Postgres.
- `docker/mihomo/` — Mihomo sidecar for **Telegram** (default **DIRECT**; optional **PROXY_SUBSCRIPTION_***).
- `setup-server.sh` — optional **VDS** bootstrap: nginx-proxy + TLS for `learnix.mikyss.ru`, then `docker compose` with the proxy overlay. If `Learnix/docker-compose.yml` is missing (e.g. shallow clone), the script writes `.setup-server.proxy-overlay.yml` in the repo root with the same effect.
   