import os
import sys

# Ensure testing environment is set before module imports
os.environ["APP_ENV"] = "testing"

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import close_db_engine, AsyncSessionLocal
from app.core.redis import close_redis

# On Windows, use SelectorEventLoop to avoid Proactor socket cleanup issues with aiomysql
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def cleanup_resources():
    """Ensure DB and Redis connection pools are disposed when test session finishes."""
    yield
    await close_db_engine()
    await close_redis()


@pytest_asyncio.fixture
async def async_client():
    """
    Async HTTP test client bound directly to the FastAPI ASGI application.
    raise_app_exceptions=False ensures Starlette/FastAPI exception handlers
    catch unhandled errors and format them as 500 JSON responses.
    """
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def db_session():
    """
    Provides an isolated async session for database testing against reliable_insurance_dev.
    Rolls back automatically at the end of each test to maintain clean state.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()

