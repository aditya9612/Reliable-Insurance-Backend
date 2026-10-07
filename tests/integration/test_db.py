import pytest
from sqlalchemy import text
from app.db.session import check_db_connection, get_db
from app.core.redis import check_redis_connection


@pytest.mark.asyncio
async def test_local_db_connectivity():
    """
    Verify async connectivity to the independent local development database.
    Confirms the connected database is strictly 'reliable_insurance_dev'.
    """
    result = await check_db_connection()
    assert result["status"] == "connected"
    assert result["database"] == "reliable_insurance_dev"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_get_db_session_lifecycle():
    """
    Verify get_db dependency yields an active AsyncSession,
    can execute queries, and closes cleanly.
    """
    session_generator = get_db()
    session = await anext(session_generator)
    try:
        query_result = await session.execute(text("SELECT 1 + 1 AS sum"))
        row = query_result.fetchone()
        assert row[0] == 2
    finally:
        try:
            await anext(session_generator)
        except StopAsyncIteration:
            pass


@pytest.mark.asyncio
async def test_redis_connection_safe_check():
    """
    Verify check_redis_connection returns a well-formed status dictionary
    without raising unhandled exceptions regardless of Redis server availability.
    """
    result = await check_redis_connection()
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] in ["connected", "disconnected"]
