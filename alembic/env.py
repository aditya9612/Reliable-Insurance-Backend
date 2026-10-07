import asyncio
import sys
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import application settings and declarative models metadata
from app.core.config import settings
from app.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate' support
target_metadata = Base.metadata

# Inject the application's local DATABASE_URL directly from settings
database_url = settings.DATABASE_URL


def verify_database_safety(connection: Connection) -> None:
    """
    CRITICAL SAFETY ENFORCEMENT:
    Ensures Alembic NEVER runs against the legacy production database or remote server.
    """
    db_name = connection.execute(text("SELECT DATABASE()")).scalar()
    if not db_name or db_name.lower() != "reliable_insurance_dev":
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: Alembic attempted to run against '{db_name}'. "
            "Alembic migrations are STRICTLY RESTRICTED to 'reliable_insurance_dev'. "
            "Execution aborted immediately."
        )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # Enforce database safety check before running any migration
    verify_database_safety(connection)
    
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using AsyncEngine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # On Windows, SelectorEventLoop avoids Proactor socket shutdown issues
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
