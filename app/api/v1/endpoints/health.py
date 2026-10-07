from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.db.session import check_db_connection
from app.core.redis import check_redis_connection

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Liveness probe.
    Does not require authentication.
    Returns 200 OK indicating the FastAPI application process is alive and accepting traffic.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0",
    }


@router.get("/ready")
async def readiness_check(response: Response):
    """
    Readiness probe.
    Verifies connectivity to the independent local development database and local Redis.
    SAFETY GUARANTEE: Does NOT connect to or touch the legacy production database.
    
    Returns 200 OK if core dependencies are operational.
    Returns 503 Service Unavailable if primary database connectivity fails.
    """
    db_status = await check_db_connection()
    redis_status = await check_redis_connection()

    is_db_ready = db_status.get("status") == "connected"
    # Local dev readiness: DB is required for traffic; Redis reports connectivity status
    is_ready = is_db_ready

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "environment": settings.APP_ENV,
        "components": {
            "database": {
                "status": db_status.get("status"),
                "database_name": db_status.get("database"),
                "error": db_status.get("error"),
            },
            "redis": {
                "status": redis_status.get("status"),
                "error": redis_status.get("error"),
            },
        },
    }
