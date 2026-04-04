import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_db, get_ollama
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.models.entities import User
from app.services.ollama import MockOllamaClient

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/sethack_test",
)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_ollama() -> MockOllamaClient:
    m = MockOllamaClient()
    m.response_queue = [
        {"explanation": "Short intro.", "task": "What is 2+2?", "rubric": "Answer 4."},
        {
            "correct": True,
            "feedback": "Correct!",
            "next_task": None,
            "session_complete": True,
        },
    ]
    return m


@pytest_asyncio.fixture
async def client(test_engine, mock_ollama) -> AsyncGenerator[AsyncClient, None]:
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ollama] = lambda: mock_ollama
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def api_headers():
    return {
        "X-API-Key": get_settings().api_secret,
        "X-Telegram-User-Id": "999001",
    }


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, api_headers) -> User:
    tid = int(api_headers["X-Telegram-User-Id"])
    u = User(telegram_id=tid, name="Test", timezone="UTC")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u
