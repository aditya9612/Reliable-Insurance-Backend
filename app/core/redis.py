import logging
from typing import Optional, Dict, Any
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client reference
redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> Optional[aioredis.Redis]:
    """
    Initializes the async Redis client connection pool.
    Called during application startup.
    """
    global redis_client
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
        )
        return redis_client
    except Exception as e:
        logger.warning(f"Redis initialization warning (will retry on demand): {e}")
        redis_client = None
        return None


async def get_redis_client() -> Optional[aioredis.Redis]:
    """
    Returns the active Redis client or creates one if not initialized.
    """
    global redis_client
    if redis_client is None:
        await init_redis()
    return redis_client


async def check_redis_connection() -> Dict[str, Any]:
    """
    Checks connectivity to the local development Redis instance.
    Safe check: returns error details rather than throwing unhandled exceptions.
    """
    try:
        client = await get_redis_client()
        if client is None:
            return {
                "status": "disconnected",
                "error": "Redis client is not initialized",
            }
        ping_response = await client.ping()
        if ping_response:
            return {
                "status": "connected",
                "error": None,
            }
        return {
            "status": "disconnected",
            "error": "Redis PING returned unexpected response",
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
        }


async def close_redis() -> None:
    """Closes Redis connections during application shutdown."""
    global redis_client
    if redis_client is not None:
        try:
            await redis_client.close()
        except Exception as e:
            logger.warning(f"Error closing Redis client: {e}")
        finally:
            redis_client = None
