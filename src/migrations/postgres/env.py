import asyncio
import os
import sys

# Ensure the project root is on the path so src.* imports work.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Import all model modules so their Tables register on postgres.metadata.
from src.api import models as _models  # noqa: F401
from src.core.postgres import metadata

config = context.config
target_metadata = metadata


def _get_url() -> str:
    url = os.environ.get('DATABASE_URL')
    if url:
        return url
    from src.core.config import get_settings

    return get_settings().database_url_str()


def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _get_url()
    connectable = create_async_engine(url)

    async def _run() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(_do_migrations)
        await connectable.dispose()

    asyncio.run(_run())


def _do_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
