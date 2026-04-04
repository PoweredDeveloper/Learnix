# Smart Study Assistant — Build Plan (AI execution)

Use this document as the **source of truth** for scope, stack, layout, and quality bar. Pair with **`AGENT.md`** when prompting coding agents.

---

## Product (one paragraph)

Telegram-first study planner with a **FastAPI** backend and **React** web UI. Users attach **prep files**; the system extracts text, calls **Ollama** for structured outputs, persists **subjects / topics / tasks / cheat sheets**, sends **daily plans** via **aiogram** with **inline keyboards** (emoji-labeled buttons), and adapts when tasks are skipped. A **single command** opens a **guided study session** (one continuous flow: mini-lesson → tasks → user answers → correct advances / incorrect gets solution check & hints). **Daily streaks** reward hitting a **minimum daily study threshold** (see below).

**Differentiation vs. a raw chat:** durable syllabus + tasks, file-grounded cheat sheets and plans, reminders, completion tracking, replanning, **session-scaffolded tutoring** with graded steps (not a free-form wall of text), and **streak accountability**.

---

## Fixed stack

| Layer            | Choice                                                        | Notes                                                                                       |
| ---------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Bot              | **aiogram** v3                                                | Async; `InlineKeyboardMarkup` + `callback_data`; avoid reply-keyboard spam after onboarding |
| API              | **FastAPI**                                                   | Async routes; Pydantic v2; OpenAPI for frontend codegen optional                            |
| ORM / DB         | **SQLAlchemy 2.x** + **Alembic**                              | Async engine (`asyncpg`) recommended; migrations required                                   |
| DB               | **PostgreSQL**                                                | Dev: Docker Compose                                                                         |
| Frontend         | **React** (Vite)                                              | TypeScript; fetch or TanStack Query to API                                                  |
| AI               | **Ollama HTTP API**                                           | `POST /api/chat` or `/api/generate`; base URL + model via env; **no** vendor SDK            |
| Tests            | **pytest** + **httpx** `AsyncClient` / Starlette `TestClient` | Unit + API integration; **Playwright** (or Cypress) for web e2e                             |
| E2E (full stack) | **Docker Compose**                                            | `api` + `db` + optional `ollama`; smoke script or Playwright against `web` + `api`          |

---

## Repository layout (suggested)

```
/backend
  /app
    /api/routes
    /core/config.py
    /models
    /schemas
    /services  # business + Ollama client + ingestion
    /db
  /tests
    /unit
    /integration
  alembic/
  pyproject.toml
/bot
  /handlers
  /keyboards
  /clients  # httpx client → backend API
  /tests
/web
  /src
  e2e/       # Playwright specs
  package.json
docker-compose.yml
PLAN.md
AGENT.md
```

- **Bot** is a separate process: it **does not** import SQLAlchemy models from `backend`; it calls **HTTP APIs** with a service token or user JWT (define in `AGENT.md` / auth section below).
- **Shared contracts:** OpenAPI or hand-written TypeScript types mirrored from Pydantic schemas; keep DRY via OpenAPI codegen only if worth the tooling cost.

---

## Backend responsibilities

- Auth: Telegram-init flow or API keys for bot — pick one for MVP and document in OpenAPI.
- CRUD: users, subjects, topics, prep uploads, study plans, study tasks, cheat sheets, progress logs.
- **Ingestion:** PDF text (e.g. `pypdf`), PPTX (e.g. `python-pptx`), plain text/Markdown; store raw path + extracted text + parsed outline JSON.
- **Ollama service:** single module wrapping HTTP calls; prompts return **JSON** (enforce with prompt + `response_format` if model supports it, else repair-parse); timeouts and retries; **injectable client** for tests (mock).
- **Guided session service:** drives one **study_session** (state + transcript tail); calls Ollama for (1) brief explanation, (2) next micro-task, (3) **grading** (`correct` / `incorrect`), (4) on incorrect, **solution review** (what the student got right/wrong, hint, optional nudge to retry same or easier variant). All steps are **one logical session** until user ends it.
- **Streak service:** once per calendar day (user **timezone**, stored on `users`), evaluate **daily quota** vs **completed work**; if completed ≥ **20%** of quota, mark day **streak-eligible** and update `streak_current` / `last_streak_date` (see **Daily streaks**).

---

## Guided study session (single command, one session)

**Entry:** one command, e.g. `/learn` (optional args: subject/topic id or name). User is now in **learn mode** until they exit.

**Flow (same chat thread, no separate commands per step):**

1. **Open session** — backend creates `study_session` (topic context, optional prep excerpt IDs).
2. **Explain** — Ollama returns short explanation of the **current sub-theme** (grounded in topic + optional prep outline).
3. **Micro-task** — Ollama emits **one small task** (easy first); store `expected_answer_rubric` or full task spec in session state (for grading).
4. **User message = answer** — not interpreted as random chat: bot routes free text to **POST /sessions/{id}/answer** (or equivalent).
5. **Branch**
   - **Correct** → advance: next micro-task or next sub-theme; same session id until topic milestone or user stops.
   - **Incorrect** → Ollama **reviews the user’s solution** (misconception, partial credit, hint); **do not** advance until policy says so (e.g. after review, offer **Retry** inline button or next easier question—product choice: default **retry one variant** then advance on second correct or explicit “skip step”).

**Exit:** `/done` or inline `🛑 End session` — persist summary (tasks attempted, correct count) for **streak / daily progress** contribution.

**State:** store session server-side (PostgreSQL table or Redis). Bot uses **FSM** (aiogram) mirrored to API so restarts don’t lose truth—or **FSM thin, API authoritative**.

**Why one command:** the user never types “next”; they only **answer**. Navigation uses **inline** actions when needed (`🔄 Retry`, `⏭ Skip step`, `🛑 End`).

---

## Daily streaks

- **Daily quota** for a user-day = sum of **estimated_minutes** (or task count fallback) for **study_tasks** scheduled **that calendar day** in the user’s timezone; if no tasks scheduled, fall back to **plan default** (e.g. 30 min goal) configurable per user.
- **Completed today** = sum of **estimated_minutes** for tasks marked **done** that day **plus** optional weight for **guided session** time (e.g. minutes in active session or N minutes per completed micro-task)—define one formula in code and **test it**.
- **Streak rule:** day counts toward streak if `completed_today / daily_quota >= 0.20` (20%). Use `>=` and cap ratio at 1.0 for display.
- **Consecutive days:** if yesterday was streak-eligible and today is too, increment `streak_current`; else reset to 1 on first eligible day after break.
- **Schema:** `users.streak_current`, `users.streak_best`, `users.last_streak_eligible_date`, `users.timezone` (IANA string).
- **UI:** bot `/streak` or dashboard widget; celebrate milestones sparingly.

---

## Bot responsibilities (aiogram)

- Commands: `/start`, `/plan`, `/progress`, `/upload`, `/cheatsheet`, `/tasks`, **`/learn`**, **`/done`** (exit learn mode), **`/streak`**.
- **`/learn`:** start or resume session; first bot message = explanation + first task; thereafter **text replies = answers**.
- **Inline keyboards** for main loops and inside learn mode (`🔄 Retry`, `⏭ Skip`, `🛑 End`); `callback_data` compact and validated (e.g. `done:<task_id>`).
- **Middleware / filters:** while `study_session` active for chat, route **non-command text** to session answer handler (not generic fallback).
- File uploads: receive document → `multipart` to backend → poll or webhook for long jobs if needed later.
- Scheduling: APScheduler or external cron hitting backend “digest” endpoint — MVP can be “user runs `/plan`” first.

---

## Frontend responsibilities (React)

- Dashboard, subjects/topics, task board, prep library, cheat sheet viewer (Markdown render), export (client-side print-to-PDF or backend PDF later).
- **Streak** display (current / best, today’s progress toward 20% threshold).
- E2E targets: login or dev bypass → create subject → list tasks → mark complete (if exposed in web).

---

## Testing strategy (mandatory)

### Unit tests (pytest)

- **Pure functions:** date/replan helpers, `callback_data` encode/decode, outline normalization, **streak eligibility** (20% rule), **timezone boundary** for “today”.
- **Services with mocks:** Ollama client (res mocked JSON), ingestion edge cases (empty PDF).
- **DB logic:** repository/service tests using **transaction rollback** or **test database** per worker.

### Integration / API tests (pytest + FastAPI)

- `httpx.AsyncClient(app=app, base_url="http://test")` or equivalent **lifespan** aware fixture.
- Real **PostgreSQL test DB** (Compose service `db_test` or ephemeral container) — avoid SQLite if you use PG-specific types.
- Cover: create user/subject, upload prep (small fixture file), generate plan endpoint (Ollama **mocked**), task status transitions, **session answer** endpoint (mocked Ollama returns `correct` / `incorrect` + review text), **streak** recompute after task completion.

### Bot tests (pytest)

- **aiogram** dispatcher tests: feed **Update** objects built from dicts; mock backend HTTP client; assert **answer** / **edit_message_text** calls; **`/learn` then a text message** routes to the session answer API (not generic chat).
- No real Telegram network in CI.

### E2E tests

- **Web:** Playwright against `web` dev server + `api` + `db`; seed data via API or SQL fixture.
- **Minimum e2e flows:** health check → primary user journey (e.g. view dashboard + tasks) as defined when UI exists.
- **Optional full-stack:** Compose profile with `ollama` + tiny model for one “smoke” generation test (can be nightly only to save CI time).

### CI expectations

- `pytest` (unit + integration) on every PR.
- `playwright install` + e2e on PR or main (choose one; document in `AGENT.md`).
- Lint: **ruff** (backend), **eslint** (frontend), format: **ruff format** / **prettier**.

---

## Ollama

- Env: `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (e.g. `llama3.2`, `qwen2.5`).
- All generation goes through **one** backend module; bot never talks to Ollama directly.
- Tests: default to **mock**; optional `OLLAMA_E2E=1` locally for real calls.

---

## Database (entities)

- Existing: `users`, `subjects`, `topics`, `prep_sources`, `study_plans`, `study_tasks`, `cheat_sheets`, `logs`.
- **users:** add `timezone`, `streak_current`, `streak_best`, `last_streak_eligible_date` (date, user TZ).
- **study_sessions:** `id`, `user_id`, `topic_id` (nullable), `status` (active/ended), `state` (JSON: phase, current_task_id, transcript refs), `started_at`, `ended_at`.
- **session_events** (optional, for analytics): `session_id`, `role` (user/assistant), `payload` (text or JSON), `created_at`.

Add `created_at` / `updated_at` everywhere on core entities.

---

## MVP order of implementation (for agents)

1. Compose: Postgres + backend skeleton + health route + Alembic initial migration + **pytest CI**.
2. Core CRUD + auth stub + **API integration tests**.
3. Ollama client + “generate outline / tasks / cheat sheet” endpoints + **unit tests** (mocked).
4. Ingestion pipeline + **fixture PDF test**.
5. aiogram bot: `/start`, `/plan` with **inline** Done/Skip + **handler tests**.
6. **`/learn` session**: API session CRUD + Ollama **grade + review** JSON contract + bot FSM/middleware + tests.
7. **Streaks**: quota/completion math + user timezone + **`/streak`** + web widget + **unit tests** for 20% edge cases (0 tasks, all done, exactly 20%).
8. React shell + list tasks + **Playwright** happy path.
9. Reminders / replan polish + more e2e.

---

## Success criteria

- Every new **route** or **handler** ships with **tests** (unit or integration as appropriate).
- **E2E** covers at least one **critical user path** on web; bot covered by **dispatcher tests** in CI.
- Ollama is **swappable** (mock in tests; real in dev/prod).
- **Guided session:** one command opens flow; user answers in chat; incorrect attempts get **solution check** before moving on; session ends explicitly.
- **Streak:** completing **≥ 20%** of that day’s quota marks the day eligible; consecutive eligible days bump streak.

---

## Appendix: callback_data convention (example)

`p:<action>:<id>` — e.g. `p:done:7f3a...` (short UUID). Validate server-side; reject unknown actions.

---

**Next implementation docs (optional):** OpenAPI outline, Alembic revision 001, first Playwright spec list.
