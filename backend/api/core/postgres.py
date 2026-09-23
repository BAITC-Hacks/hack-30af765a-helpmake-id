"""Small async PostgreSQL connection boundary for SQLAlchemy Core models."""

import functools
import os

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

metadata = sa.MetaData()


def database_url() -> str:
    url = os.getenv('DATABASE_URL', '').strip()
    if not url.startswith('postgresql+asyncpg://'):
        raise RuntimeError('DATABASE_URL must use postgresql+asyncpg://')
    return url


@functools.lru_cache(maxsize=4)
def _engine(url: str) -> AsyncEngine:
    return create_async_engine(url, poolclass=sa.pool.NullPool)


def session(function):
    """Give one model operation a short database transaction."""

    @functools.wraps(function)
    async def wrapped(*args, **kwargs):
        async with _engine(database_url()).begin() as connection:
            return await function(connection, *args, **kwargs)

    return wrapped
