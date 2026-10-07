import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.logging import StructuredLoggingMiddleware
from app.middleware.exception_handler import register_exception_handlers
from app.core.redis import init_redis, close_redis
from app.db.session import close_db_engine, check_db_connection

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("reliable.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle management.
    Initializes resource pools (DB engine, Redis) and cleans up gracefully on termination.
    """
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    
    # Check independent local database connectivity
    db_status = await check_db_connection()
    if db_status.get("status") == "connected":
        logger.info(f"Connected to local development database: {db_status.get('database')}")
    else:
        logger.warning(f"Local database connection warning: {db_status.get('error')}")

    # Initialize local Redis client
    await init_redis()
    
    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")
    await close_redis()
    await close_db_engine()
    logger.info("Resources gracefully released.")


def create_application() -> FastAPI:
    """
    Application factory for Reliable Assurance FastAPI Backend.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="FastAPI Backend for Reliable Assurance (Modernized from Legacy .NET 4.0)",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 2. Structured Logging Middleware (Outer)
    app.add_middleware(StructuredLoggingMiddleware)

    # 3. Request ID Correlation Middleware (Innermost request boundary)
    app.add_middleware(RequestIdMiddleware)

    # 4. Centralized Exception Handlers
    register_exception_handlers(app)

    # 5. API V1 Routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "app": settings.APP_NAME,
            "version": "1.0.0",
            "environment": settings.APP_ENV,
            "status": "running",
            "docs": "/docs" if settings.DEBUG else "disabled",
        }

    return app


app = create_application()
