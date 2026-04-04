# Agent instructions — Smart Study Assistant

When working on this repository, **read `PLAN.md` first**. This file defines **how** to implement: conventions, boundaries, and what to verify before finishing.

---

## Stack (do not swap without updating `PLAN.md`)

- **Bot:** Python, **aiogram** v3 (async).
- **Backend:** **FastAPI**, **SQLAlchemy 2.x**, **Alembic**, **PostgreSQL** (async driver preferred).
- **Frontend:** **React** + TypeScript (Vite).
- **AI:** **Ollama** HTTP API only — called from **backend**, never from the browser or bot directly.

---

## Architecture rules

1. **Bot → Backend via HTTP** only (httpx/aiohttp client). No shared ORM models between `bot/` and `backend/`.
2. **Single Ollama wrapper** in backend (`services/ollama.py` or equivalent): timeouts, structured JSON prompts, errors mapped to HTTP 502/504 where appropriate.
3. **Pydantic schemas** are the contract for API; mirror types on frontend or generate from OpenAPI if tooling is added.
4. **Migrations:** every schema change gets an **Alembic** revision; no manual “fix prod DB” instructions as the only path.

---

## Telegram UX

- Use **inline keyboards** for primary actions after onboarding; emoji + short label (e.g. `✅ Done`, `⏭ Skip`).
- Keep `callback_data` small and parseable; validate on server.
- Prefer **editing** the message on callback to reduce chat noise.

### Guided learn mode (`/learn`)

- **One command** starts a **session**; user progress is **free-text answers** in the same chat until **`/done`** or inline **End**.
- While a session is **active**, route **non-command messages** to the backend **answer** endpoint (middleware/FSM); do not treat them as unrelated small talk.
- **Backend owns session state** (DB); bot FSM can be a thin cache. Ollama responses for grading must be **structured** (e.g. `correct: bool`, `review_for_user: str`, optional `next_action`).
- On **incorrect**: always return a **solution check** (what was wrong, hints); policy for **retry vs. skip** must match `PLAN.md` (inline `🔄` / `⏭`).

### Streaks

- Streak day is **eligible** when the user completes **≥ 20%** of **daily quota** (see `PLAN.md`). Implement in a **pure, tested** function; respect **user timezone** for calendar boundaries.
- Updating streaks runs when tasks/session progress changes **or** on a daily job—pick one consistent approach and test it.

---

## Testing — required with every change

| Change type                  | Minimum tests                                                                   |
| ---------------------------- | ------------------------------------------------------------------------------- |
| New pure logic               | **Unit** (`pytest`)                                                             |
| New API route                | **Integration** test with real PG test DB + mocked Ollama unless explicitly e2e |
| New bot handler              | **Dispatcher test** with mocked backend client                                  |
| Learn session / streak logic | **Unit** for math + timezone; **integration** for session POST + mocked Ollama  |
| New web flow (user-visible)  | **Playwright** (or add to existing e2e) when the flow is stable                 |

- **Never** commit Ollama-dependent tests that call the network without `OLLAMA_E2E` or similar guard.
- Prefer **factories/fixtures** for users/subjects/tasks over duplicated setup.

---

## Commands agents should run (when code exists)

- Backend: `pytest` from `backend/` (or repo root if configured).
- Frontend: `npm test` / `npm run lint` / `npm run build` as defined in `package.json`.
- E2E: `npx playwright test` (after `playwright install`).

Fix failures before declaring work complete.

---

## Config / secrets

- Use **environment variables** (`.env.example` checked in; `.env` gitignored).
- Bot token, DB URL, API service secret, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` — document each in `.env.example`.

---

## Style

- Python: **ruff** + type hints on public APIs; async end-to-end in bot and async FastAPI routes.
- TypeScript: strict mode; avoid `any` on API boundaries.
- Keep diffs **focused**; do not refactor unrelated modules.

---

## Definition of done

1. Matches `PLAN.md` scope for the task.
2. Tests added/updated and **passing**.
3. No new secrets in repo; env vars documented if new.
4. If DB schema changed: **migration included**.

---

## Prompting hint for users

> “Follow `PLAN.md` and `AGENT.md`. Implement X with tests; bot uses aiogram inline keyboards; AI via backend Ollama client only; `/learn` sessions route answers to the API; streaks use the 20% daily-quota rule.”
