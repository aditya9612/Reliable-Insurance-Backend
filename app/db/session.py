from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from app.core.config import settings

# Determine pool kwargs based on environment (NullPool for testing ensures loop isolation)
pool_kwargs: Dict[str, Any] = {}
if settings.APP_ENV == "testing":
    pool_kwargs["poolclass"] = NullPool
else:
    pool_kwargs["pool_size"] = settings.DB_POOL_SIZE
    pool_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    pool_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE
    pool_kwargs["pool_pre_ping"] = True

# Create async engine with robust connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    **pool_kwargs
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session.
    Automatically handles session lifecycle and cleanup.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> Dict[str, Any]:
    """
    Verifies connectivity to the independent local development database.
    Does NOT connect to the legacy production database.
    """
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT DATABASE(), 1 AS ping"))
            row = result.fetchone()
            current_db = row[0] if row else "unknown"
            return {
                "status": "connected",
                "database": current_db,
                "error": None,
            }
    except Exception as e:
        return {
            "status": "disconnected",
            "database": None,
            "error": str(e),
        }


async def close_db_engine() -> None:
    """Disposes engine pool during application shutdown."""
    await engine.dispose()
