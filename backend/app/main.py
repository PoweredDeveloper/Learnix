from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cheat_sheet, courses, health, lessons, plan, prep, sessions, streak, subjects, tasks, users
from app.core.config import get_settings
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="Smart Study Assistant API", lifespan=lifespan)
settings = get_settings()
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(subjects.router)
app.include_router(tasks.router)
app.include_router(sessions.router)
app.include_router(streak.router)
app.include_router(plan.router)
app.include_router(prep.router)
app.include_router(lessons.router)
app.include_router(cheat_sheet.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "sethack-api", "docs": "/docs"}
