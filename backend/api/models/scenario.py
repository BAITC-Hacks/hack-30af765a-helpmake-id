"""Saved scenarios in PostgreSQL; schema changes are applied by Alembic."""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from ..core import postgres

Scenarios = sa.Table(
    'scenarios',
    postgres.metadata,
    sa.Column('id', sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column('name', sa.Text, nullable=False),
    sa.Column('decisions', postgresql.JSONB, nullable=False),
    sa.Column('dataset_version', sa.Text, nullable=False),
    sa.Column('dataset_hash', sa.Text, nullable=False),
    sa.Column('result', postgresql.JSONB, nullable=False),
    sa.Column('score', sa.Float, nullable=False),
    sa.Column('spent', sa.Integer, nullable=False),
    sa.Column('budget', sa.Integer, nullable=False),
    sa.Column(
        'created_at',
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Index('ix_scenarios_created_at', 'created_at'),
)

AlembicVersion = sa.table(
    'alembic_version',
    sa.column('version_num', sa.String(32)),
)
SCHEMA_REVISION = '20260923_01'


@postgres.session
async def ready(connection) -> bool:
    revision = (await connection.execute(sa.select(AlembicVersion.c.version_num))).scalar_one()
    if revision != SCHEMA_REVISION:
        return False
    await connection.execute(sa.select(Scenarios.c.id).limit(1))
    return True


@postgres.session
async def create(connection, data: dict) -> dict:
    record = {'id': str(uuid.uuid4()), **data}
    row = (
        await connection.execute(sa.insert(Scenarios).values(**record).returning(*Scenarios.c))
    ).one()
    return dict(row._mapping)


@postgres.session
async def get(connection, scenario_id: str) -> dict | None:
    row = (
        await connection.execute(sa.select(Scenarios).where(Scenarios.c.id == scenario_id))
    ).first()
    return dict(row._mapping) if row is not None else None


@postgres.session
async def list_scenarios(connection, limit: int, offset: int) -> list[dict]:
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
    rows = (
        await connection.execute(
            sa.select(*columns)
            .order_by(Scenarios.c.created_at.desc(), Scenarios.c.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [dict(row._mapping) for row in rows]


@postgres.session
async def delete(connection, scenario_id: str) -> bool:
    row = (
        await connection.execute(
            sa.delete(Scenarios).where(Scenarios.c.id == scenario_id).returning(Scenarios.c.id)
        )
    ).first()
    return row is not None
