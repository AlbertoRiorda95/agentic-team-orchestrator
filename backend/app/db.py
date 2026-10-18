"""Database engine and the readiness probe."""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

logger = logging.getLogger(__name__)


def create_engine(database_url: str) -> AsyncEngine:
    # pre-ping: a connection broken by a database restart is replaced, not reused
    return create_async_engine(database_url, pool_pre_ping=True)


async def database_is_ready(engine: AsyncEngine, time_limit: float) -> bool:
    """True when `SELECT 1` succeeds within `time_limit` seconds."""
    try:
        async with asyncio.timeout(time_limit), engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except TimeoutError:
        logger.warning("database check timed out after %.1f s", time_limit)
        return False
    except Exception as exc:
        # the exception text can carry connection details: log only its type
        logger.warning("database check failed: %s", type(exc).__name__)
        return False
    return True
