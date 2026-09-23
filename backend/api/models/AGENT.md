# Model Conventions

These instructions apply to model modules in `src/api/models/`.

## Layer Responsibility

Models own **all application SQL and persistence operations**. See
`src/api/CLAUDE.md` for the full layer contract.

The baseline every table exposes is the standard SQLAlchemy CRUD surface —
`<entity>_create`, `<entity>_get`, `<entity>_list`, `<entity>_update`,
`<entity>_delete` (plus `<entity>_upsert`/`<entity>_search` where needed), built
with SQLAlchemy Core statements. Beyond that baseline, models also own:

- Atomic and conditional updates (state transitions expressed as a single
  guarded UPDATE, fenced updates, claim-and-flip statements).
- Cross-table database queries, reports, traces, and backlog counts.
- Transaction scopes and transaction-aware functions. An outer model function
  passes its session to nested model functions when several persistence
  operations must commit together.
- Constraint-to-domain-exception translation.

A model function returns **database facts** — "row already existed", "conditional
update affected zero rows", "current persisted status" — and lets the controller
decide the business outcome.

Models must **not** contain:

- Use-case policy or provider/business outcome selection — that belongs in `controllers/`.
- Provider/HTTP handling or outbound calls — that belongs in `webhooks/`.
- API request/response concerns — that belongs in `schemas/`.

## Input Values

- Prefer plain primitive `dict` inputs for create, update, and upsert functions.
  Controllers validate Pydantic schemas and call
  `model_dump(mode='json', by_alias=True)` before invoking the model.
- Models do not call `model_dump()` for ordinary request/command persistence and
  should not depend on Pydantic request schemas merely to write a row.
- Copy an input dictionary before mutating it inside a model function when the
  caller's object must remain unchanged.
- Keep identifiers, filters, limits, offsets, expected statuses/versions, and
  focused database-operation inputs as explicit typed parameters.
- Update dictionaries contain the complete desired values for all mutable
  persisted fields. Apply them directly with one guarded `UPDATE`; do not
  implement partial updates by filtering missing/`None` values or by reading and
  merging the existing row.

## SQLAlchemy-Only Database Access

- Construct all application database operations with SQLAlchemy Core.
- Do not execute raw SQL strings. Build queries and writes from SQLAlchemy
  tables, columns, functions, and expression objects.
- Do not use PostgreSQL triggers, stored procedures, or stored functions for
  application behavior or persistence invariants.
- Express schema invariants in the SQLAlchemy table definition with nullability,
  server defaults, foreign keys, unique constraints, check constraints, and
  indexes, including partial unique indexes when required.
- Express state-dependent writes as guarded SQLAlchemy `UPDATE`, `INSERT ... ON
  CONFLICT`, or `DELETE` statements and inspect their returned row/row count.
- Translate only known, named constraint violations into model exceptions or
  plain dictionary outcomes. Unknown database errors propagate.
- Match structured exception attributes such as `constraint_name`; do not parse
  human-readable database error strings.

## No Explicit Database Locks

Application code must not explicitly acquire pessimistic PostgreSQL locks. Do
not use:

- `.with_for_update()` or `SELECT ... FOR UPDATE` / `FOR SHARE`.
- `NOWAIT` or `SKIP LOCKED`.
- PostgreSQL advisory locks.
- `LOCK TABLE`.

Keep transactions short and database-only, use bounded batches, and honor
configured statement and lock timeouts. Never call a provider, webhook, HTTP
endpoint, filesystem, queue, or other external service while a transaction is
open.

## Return Values

- Every public model operation returns plain Python data. A singular record or
  operation outcome is always a `dict`; a collection is `list[dict]`.
- Convert SQLAlchemy result rows with `dict(row)` before returning them.
- Do not return SQLAlchemy rows, Pydantic schemas, ORM instances, tuples, enums,
  or custom result objects across the model boundary.
- A mutation with no entity response returns an outcome dictionary such as
  `{'applied': True}` rather than `None` or a bare boolean/scalar.

## Sessions and Transactions

Every database entrypoint uses `@postgres.session`. Controllers call decorated
model functions without a session. The decorator acquires/releases a session for
a top-level call and reuses an explicitly passed session for nested model calls.

The decorator does **not** automatically make multiple statements atomic. An
outer model function must open `session.transaction()` and pass `session`
explicitly to every nested model function:

```python
@postgres.session
async def entity_create_with_event(session, entity, event):
    async with session.transaction():
        created = await entity_insert(session, entity)
        await models.append_event(
            session,
            'entity',
            created['id'],
            event['type'],
            event['payload'],
        )
    return created
```

## Imports

```python
import typing
import uuid

import asyncpg.exceptions
import sqlalchemy
import sqlalchemy.dialects.postgresql

from ...core import postgres
from .. import models
```

## Domain Exceptions

All reusable custom domain and persistence exception classes are declared in the
relevant model module. Define them before the table, export them from
`models/__init__.py`, and reference them as `models.<Exception>` from
controllers and other layers that may import models. Controllers must not define
custom domain exception classes.

Naming pattern: `<Entity><Condition>`.

```python
class EntityDoesNotExist(Exception):
    """Raised when the entity is not found."""


class EntityNameAlreadyInUse(Exception):
    """Raised when an entity with the same name already exists."""


class EntityInUse(Exception):
    """Raised when an entity cannot be deleted because it is referenced."""
```

## Filter Type Alias

```python
EntityFilters = typing.Union[
    sqlalchemy.sql.expression.BinaryExpression,
    sqlalchemy.sql.expression.BooleanClauseList,
]
```

## Pagination Metadata

Declares sortable columns for cursor-based pagination. Always include `id` last for tie-breaking.

```python
entity_pagination = {
    'columns': [
        {'name': 'name', 'type': str},
        {'name': 'id', 'type': int},
    ],
}
```

## Table Definition

Use `sqlalchemy.Table` with `postgres.metadata` (SQLAlchemy Core, not ORM).

```python
Entity = sqlalchemy.Table(
    'entity',
    postgres.metadata,
    sqlalchemy.Column(
        'id',
        sqlalchemy.UUID(as_uuid=True),
        primary_key=True,
        server_default=sqlalchemy.text('uuid_generate_v4()'),
    ),
    sqlalchemy.Column(
        'name',
        sqlalchemy.Text,
        nullable=False,
    ),
    sqlalchemy.Column(
        'is_active',
        sqlalchemy.Boolean,
        nullable=False,
        server_default=sqlalchemy.text('true'),
    ),
    sqlalchemy.Column(
        'organization_id',
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey('organization.id'),
        nullable=False,
        index=True,
    ),
    sqlalchemy.Column(
        'created_at',
        sqlalchemy.DateTime(timezone=True),
        nullable=False,
        server_default=sqlalchemy.text('now()'),
    ),
    sqlalchemy.UniqueConstraint(
        'name',
        'organization_id',
    ),
)
```

### Column Conventions

- **PKs:** `id` — integer auto-increment or UUID (`server_default=sqlalchemy.text('uuid_generate_v4()')`)
- **FKs:** `<entity>_id` naming — always indexed
- **Timestamps:** `*_at` suffix, `DateTime(timezone=True)`, `server_default=sqlalchemy.text('now()')`
- **Booleans:** `is_*` prefix, `server_default='true'` or `'false'`
- **Text:** always `sqlalchemy.Text` (not `String`)
- **Finite categorical values:** use a named native PostgreSQL enum declared
  directly on the column with `sqlalchemy.dialects.postgresql.ENUM`. Use a
  stable globally unique type name such as `<table>_<column>_enum`.
- **JSONB:** `sqlalchemy.dialects.postgresql.JSONB`
- **Arrays:** `sqlalchemy.dialects.postgresql.ARRAY(sqlalchemy.Integer)`
- **Many-to-many:** bridge table with `PrimaryKeyConstraint` on both FK columns

### `default` vs `server_default`

- `default=value` is a SQLAlchemy client-side default applied by SQLAlchemy when
  an application-built INSERT omits that column. It is not database DDL.
- `server_default=value` is a database default defined in DDL and represented in
  Alembic. Use it when inserts outside the application model must receive the default.
- Choose intentionally and keep values aligned.

### Index Naming

`ix_<table>_<columns>`. Use `postgresql_using='gin'` for text search, `'gist'` for geometry.

## Query Builder

Returns a base SELECT; used by list/get/find. Applies optional filters and ordering.

```python
def entity_query(organization_id, filters=None, limit=None):
    query = (
        Entity.select()
        .where(
            Entity.c.organization_id == organization_id,
        )
        .order_by(Entity.c.name, Entity.c.id)
    )
    if filters is not None:
        query = query.where(filters)
    if limit is not None:
        query = query.limit(limit)
    return query
```

## CRUD Functions

Every table exposes this baseline. All functions use the `@postgres.session`
decorator, are `async`, and return a plain `dict` (or `list[dict]` for collections).

### Create

```python
@postgres.session
async def entity_create(session, entity: dict):
    data = dict(entity)
    query = Entity.insert().values(**data).returning(Entity.c.id)
    try:
        result = await session.fetch_one(query)
    except asyncpg.exceptions.UniqueViolationError as e:
        if e.constraint_name == 'uq_entity_name_organization_id':
            raise EntityNameAlreadyInUse from e
        raise
    return await entity_get(session, result['id'])
```

### Get

```python
@postgres.session
async def entity_get(session, entity_id: uuid.UUID):
    query = entity_query().where(Entity.c.id == entity_id)
    entity = await session.fetch_one(query)
    if entity is None:
        raise EntityDoesNotExist
    return dict(entity)
```

### List

```python
@postgres.session
async def entity_list(session, limit: int, filters=None):
    query = (
        entity_query(filters)
        .order_by(Entity.c.created_at.asc(), Entity.c.id.asc())
        .limit(limit)
    )
    return [dict(row) for row in await session.fetch_all(query)]
```

### Update

```python
@postgres.session
async def entity_update(session, entity_id: uuid.UUID, updates: dict):
    data = dict(updates)
    query = (
        Entity.update().where(Entity.c.id == entity_id).values(**data).returning(Entity.c.id)
    )
    try:
        result = await session.fetch_one(query)
    except asyncpg.exceptions.UniqueViolationError as e:
        if e.constraint_name == 'uq_entity_name_organization_id':
            raise EntityNameAlreadyInUse from e
        raise
    if result is None:
        raise EntityDoesNotExist
    return await entity_get(session, result['id'])
```

### Delete

```python
@postgres.session
async def entity_delete(session, entity_id: uuid.UUID):
    query = Entity.delete().where(Entity.c.id == entity_id).returning(Entity.c.id)
    result = await session.fetch_one(query)
    if result is None:
        raise EntityDoesNotExist
    return dict(result)
```

### Upsert (provider sync)

```python
@postgres.session
async def entity_upsert(session, entity: dict):
    data = dict(entity)
    insert = sqlalchemy.dialects.postgresql.insert(Entity).values(**data)
    query = insert.on_conflict_do_update(
        constraint='uq_entity_external_id',
        set_={k: insert.excluded[k] for k in data if k != 'external_id'},
    ).returning(Entity.c.id)
    result = await session.fetch_one(query)
    return dict(result)
```

## Constraint Translation

```python
try:
    result = await session.fetch_one(query)
    return dict(result)
except asyncpg.exceptions.UniqueViolationError as e:
    if e.constraint_name == 'entity_name_organization_id_key':
        raise EntityNameAlreadyInUse from e
    raise
except asyncpg.exceptions.ForeignKeyViolationError as e:
    if e.constraint_name == 'entity_organization_id_fkey':
        raise models.OrganizationDoesNotExist from e
    raise
```

Only translate named, expected constraints. Unknown errors must propagate.

## Required Pattern

- Define SQLAlchemy Core `sqlalchemy.Table` objects bound to `postgres.metadata`.
- Keep table definitions explicit: primary keys, foreign keys, nullability,
  server defaults, unique constraints, and indexes.
- Define all reusable custom domain and persistence exceptions here.
- Use async functions with the `@postgres.session` decorator.
- Prefer primitive dictionaries for create/update/upsert data.
- Use SQLAlchemy Core only. Do not execute raw SQL, create database triggers, or
  acquire explicit locks.
- Own transaction scopes in models. Pass an outer model function's session to
  nested model functions for one atomic unit of work.
- Return singular records and outcomes as plain dictionaries and collections as
  lists of dictionaries.
- Translate known `asyncpg` constraint errors into domain exceptions. Re-raise
  unknown errors.
- Export tables, exceptions, pagination config, and public functions from
  `models/__init__.py`.
