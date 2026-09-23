import contextlib
import functools
import typing

import sqlalchemy
import sqlalchemy.ext.asyncio

from . import config

metadata = sqlalchemy.MetaData()

_engine: sqlalchemy.ext.asyncio.AsyncEngine | None = None


class Session:
    """Wraps an async SQLAlchemy connection with a model-friendly interface."""

    def __init__(self, conn: sqlalchemy.ext.asyncio.AsyncConnection) -> None:
        self._conn = conn
        self._depth = 0

    async def fetch_one(
        self,
        query: typing.Any,
    ) -> dict | None:
        result = await self._conn.execute(query)
        row = result.mappings().first()
        return dict(row) if row is not None else None

    async def fetch_all(
        self,
        query: typing.Any,
    ) -> list[dict]:
        result = await self._conn.execute(query)
        return [dict(r) for r in result.mappings().all()]

    async def execute(
        self,
        query: typing.Any,
    ) -> sqlalchemy.engine.CursorResult:
        return await self._conn.execute(query)

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncGenerator['Session', None]:
        if self._depth == 0:
            async with self._conn.begin():
                self._depth += 1
                try:
                    yield self
                finally:
                    self._depth -= 1
        else:
            async with self._conn.begin_nested():
                self._depth += 1
                try:
                    yield self
                finally:
                    self._depth -= 1


def get_engine() -> sqlalchemy.ext.asyncio.AsyncEngine:
    global _engine
    if _engine is None:
        settings = config.get_settings()
        _engine = sqlalchemy.ext.asyncio.create_async_engine(
            settings.database_url_str(),
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _engine


@contextlib.asynccontextmanager
async def _acquire() -> typing.AsyncGenerator[Session, None]:
    engine = get_engine()
    async with engine.connect() as conn:
        yield Session(conn)


def session(fn: typing.Callable) -> typing.Callable:
    """Decorator: injects a Session as the first argument.

    When a Session instance is already the first positional argument (nested
    model call), it is passed through unchanged. Otherwise a new connection
    is acquired from the pool for this call.
    """

    @functools.wraps(fn)
    async def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        if args and isinstance(args[0], Session):
            return await fn(*args, **kwargs)
        async with _acquire() as sess:
            return await fn(sess, *args, **kwargs)

    return wrapper


async def check_connection() -> bool:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text('SELECT 1'))
        return True
    except Exception:
        return False


async def on_startup() -> None:
    get_engine()


async def on_shutdown() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
