"""Durable SQLite persistence for the unauthenticated hackathon MVP."""

import asyncio
import datetime
import functools
import os
import threading
import uuid
from pathlib import Path

import sqlalchemy as sa

metadata = sa.MetaData()

SchemaVersion = sa.Table(
    'schema_version',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('version', sa.Integer, nullable=False),
)

Scenarios = sa.Table(
    'scenarios',
    metadata,
    sa.Column('id', sa.String(36), primary_key=True),
    sa.Column('name', sa.String(120), nullable=False),
    sa.Column('decisions', sa.JSON, nullable=False),
    sa.Column('dataset_version', sa.String(32), nullable=False),
    sa.Column('dataset_hash', sa.String(64), nullable=False),
    sa.Column('result', sa.JSON, nullable=False),
    sa.Column('score', sa.Float, nullable=False),
    sa.Column('spent', sa.Integer, nullable=False),
    sa.Column('budget', sa.Integer, nullable=False),
    sa.Column('created_at', sa.String(40), nullable=False),
    sa.Index('ix_scenarios_created_at', 'created_at'),
)

_schema_lock = threading.Lock()
_schema_ready: set[str] = set()


def _database_path() -> str:
    configured = os.getenv('SCENARIO_DB_PATH')
    path = (
        Path(configured)
        if configured
        else Path(__file__).resolve().parents[2] / 'var' / 'scenarios.sqlite3'
    )
    return str(path.absolute())


@functools.lru_cache(maxsize=16)
def _engine(path: str) -> sa.Engine:
    return sa.create_engine(
        f'sqlite:///{path}',
        connect_args={'timeout': 30, 'check_same_thread': False},
    )


def _ensure_schema(path: str) -> sa.Engine:
    engine = _engine(path)
    if path in _schema_ready:
        return engine
    with _schema_lock:
        if path in _schema_ready:
            return engine
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with engine.begin() as connection:
            inspector = sa.inspect(connection)
            if inspector.has_table('schema_version'):
                version = connection.execute(
                    sa.select(SchemaVersion.c.version)
                ).scalar_one_or_none()
                if version != 1 or not inspector.has_table('scenarios'):
                    raise RuntimeError('Unsupported scenario database schema version.')
            elif inspector.has_table('scenarios'):
                raise RuntimeError('Unversioned scenario database cannot be opened.')
            else:
                metadata.create_all(connection)
                connection.execute(sa.insert(SchemaVersion).values(id=1, version=1))
        _schema_ready.add(path)
    return engine


def _create(data: dict) -> dict:
    engine = _ensure_schema(_database_path())
    record = {
        'id': str(uuid.uuid4()),
        'created_at': datetime.datetime.now(datetime.UTC).isoformat(),
        **data,
    }
    with engine.begin() as connection:
        connection.execute(sa.insert(Scenarios).values(**record))
    return record


def _get(scenario_id: str) -> dict | None:
    engine = _ensure_schema(_database_path())
    with engine.connect() as connection:
        row = connection.execute(
            sa.select(Scenarios).where(Scenarios.c.id == scenario_id)
        ).first()
    return dict(row._mapping) if row is not None else None


def _list(limit: int, offset: int) -> list[dict]:
    engine = _ensure_schema(_database_path())
    columns = (
        Scenarios.c.id,
        Scenarios.c.name,
        Scenarios.c.dataset_version,
        Scenarios.c.dataset_hash,
        Scenarios.c.score,
        Scenarios.c.spent,
        Scenarios.c.budget,
        Scenarios.c.created_at,
    )
    with engine.connect() as connection:
        rows = connection.execute(
            sa.select(*columns)
            .order_by(Scenarios.c.created_at.desc(), Scenarios.c.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    return [dict(row._mapping) for row in rows]


def _delete(scenario_id: str) -> bool:
    engine = _ensure_schema(_database_path())
    with engine.begin() as connection:
        result = connection.execute(sa.delete(Scenarios).where(Scenarios.c.id == scenario_id))
    return result.rowcount > 0


def _ready() -> bool:
    engine = _ensure_schema(_database_path())
    with engine.connect() as connection:
        return connection.execute(sa.select(SchemaVersion.c.version)).scalar_one() == 1


async def ready() -> bool:
    return await asyncio.to_thread(_ready)


async def create(data: dict) -> dict:
    return await asyncio.to_thread(_create, data)


async def get(scenario_id: str) -> dict | None:
    return await asyncio.to_thread(_get, scenario_id)


async def list_scenarios(limit: int, offset: int) -> list[dict]:
    return await asyncio.to_thread(_list, limit, offset)


async def delete(scenario_id: str) -> bool:
    return await asyncio.to_thread(_delete, scenario_id)
