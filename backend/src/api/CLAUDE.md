# API Conventions

These instructions apply to `backend/src/api/`. They describe the required
end-to-end pattern for adding or changing API resources.

## Layer Architecture

This codebase has a fixed set of layers with non-overlapping responsibilities.
There is **no general application-service layer**: `services/` hosts long-running
processes only, **controllers own business orchestration**, and **models own all
application SQL and persistence operations**.

| Layer | Owns | Must not contain |
|---|---|---|
| `schemas/` | Pydantic request/response schemas, external validation, serialization | SQL, transactions, provider calls, orchestration |
| `models/` | Tables, constraints, indexes, query builders, CRUD, sessions and transaction scopes, atomic/conditional updates, cross-table queries/reports, transactional persistence workflows, domain exception declarations, constraint→exception translation | Provider/HTTP handling, use-case policy, provider/business outcome mapping, explicit database locks, raw SQL, triggers |
| `controllers/` | Business rules, state-machine policy, use-case orchestration, and business outcomes | Database sessions or transactions, raw SQL, `Table.select/insert/update`, `session.fetch_*`/`session.execute`, custom domain exception declarations, HTTP client implementation |
| `webhooks/` | External protocol adapters: authentication, parsing, payload construction, provider response mapping, outbound HTTP | SQL, database transactions, business state machines |
| `services/` | Process lifecycle: startup/shutdown, scheduling, periodic loops | Business rules, SQL, large use-case implementations |
| `v1/endpoints/`, `cli/` | Framework/boundary wiring and error/output mapping | SQL, business workflows |
| `migrations/` | Deployment DDL and data migration | Runtime orchestration |

**Clarifications:**

- **Controllers are not HTTP-only.** A webhook, CLI command, or scheduled
  service may call a controller. Controllers are the single home for a business
  use case regardless of which boundary triggers it.
- **Controllers never own database context.** They do not use
  `@postgres.session`, accept or pass a `session`, import `postgres` to open a
  transaction, or construct/execute SQL. When several persistence operations
  must commit atomically, the controller calls one outer model function that
  owns the session and transaction and composes nested model functions.
- **A service process is thin.** It schedules a unit of work and invokes a
  controller. Business use cases belong in controllers.
- **Domain exceptions are model-owned.** Declare reusable custom business and
  persistence exception classes in the relevant `models/<domain>.py` module,
  export them from `models/__init__.py`, and raise or translate them in
  controllers as needed. Controllers must not declare custom domain exception
  classes.

## Schema-to-Database Data Flow

The normal create/update flow is:

```text
Pydantic schema
    -> controller validates/orchestrates and calls model_dump(mode='json')
    -> model receives primitive dict and performs SQLAlchemy persistence
    -> model returns dict or list[dict]
    -> FastAPI response schema validates and serializes the result
```

- Request and command schemas, including string-backed enums, belong in
  `schemas/`.
- Controllers receive schema instances and convert them to dictionaries before
  calling create/update/upsert model functions whenever practical. Use
  `mode='json'` so enum members and other serializable schema values become
  primitive persistence values; use `by_alias=True` when aliases are part of the
  stored/provider contract. Updates dump the complete validated schema; do not
  use `exclude_unset`, `exclude_defaults`, or `exclude_none` to create a sparse
  update dictionary. Use `exclude={'field_name'}` only for schema fields handled
  separately and never written into that table, such as uploaded files, nested
  commands, or transport-only metadata.
- Controllers add business-derived fields such as the current organization,
  actor identity, or externally computed values to that dictionary before the
  model call.
- Models accept those dictionaries and do not call `model_dump()` themselves.
  Scalar IDs, filters, pagination inputs, expected statuses/versions, and other
  focused operation parameters should remain typed scalar arguments rather than
  being forced into a dictionary.
- Models return primitive dictionaries. Controllers must not return SQLAlchemy
  rows, and models must not return Pydantic objects or Python enum instances.

### Full-update rule

- Update schemas represent the complete desired state of all mutable persisted
  fields, not a patch. Mutable fields remain required unless the API contract
  explicitly defines a default or allows `None` as a submitted value.
- Controllers serialize the whole validated update schema with
  `model_dump(mode='json', by_alias=True)` and add controller-owned fields.
- Models apply the complete update dictionary with one guarded SQLAlchemy
  `UPDATE`. They do not fetch the old row to merge missing input fields.
- Do not introduce PATCH-like semantics, sparse update dictionaries, or
  `exclude_unset=True`.

**Application database SQL lives only in `models/`.** The only permitted
infrastructure exceptions are `migrations/`, `core/postgres.py`, and
catalog-level migration preflight code, and each such exception must be
documented where it occurs.

**Model vs. controller discriminator:**

> Does this function *execute or construct* a database operation, or does it
> *decide why and when* database operations happen?

The former belongs in `models/`; the latter belongs in `controllers/`. A model
may use constraints and guarded SQLAlchemy statements to re-check expected
database state and coordinate several writes in one short transaction, but the
controller supplies the intended action or policy input and maps the returned
database fact to a business outcome.

## Database Safety

- Use SQLAlchemy Core for all application database access. Do not execute raw SQL
  strings; build queries and writes from SQLAlchemy tables, columns, functions,
  and expression objects. Do not use database stored procedures, stored
  functions, or triggers for application behavior.
- Do not explicitly acquire pessimistic database locks. This prohibits
  `.with_for_update()`, `FOR UPDATE`, `FOR SHARE`, `NOWAIT`, `SKIP LOCKED`,
  advisory locks, and `LOCK TABLE`.
- Normal PostgreSQL row/index locking performed internally by `INSERT`, `UPDATE`,
  and `DELETE` is unavoidable. Keep transactions short and database-only, use
  small bounded batches, and respect configured statement and lock timeouts.
- Never perform network, provider, filesystem, queue, or other external I/O while
  a database transaction is open.
- Enforce persistence invariants with SQLAlchemy-declared foreign keys, unique or
  partial unique indexes, check constraints, and atomic conditional statements
  such as `UPDATE ... WHERE <expected state> RETURNING ...`.
- A preceding read is not authoritative for a later write. Repeat mutable
  preconditions in the write predicate or enforce them with a constraint.

## Result Types

- A public model operation returning one record or outcome returns a plain
  `dict`. A collection operation returns `list[dict]`.
- Do not return SQLAlchemy row objects, Pydantic model instances, ORM objects,
  tuples, or model-specific result classes across the model boundary.
- FastAPI routes declare `schemas/` response models; FastAPI performs validation
  and serialization from the plain dictionaries returned through controllers.

## Enum Types and Defaults

- API/input/output enums live in `schemas/` and inherit from
  `(str, enum.Enum)`. Their values exactly match the external or persisted
  strings.
- Finite database categories use an explicitly named native
  `sqlalchemy.dialects.postgresql.ENUM` in the table model. List the stored
  strings directly in the database type; do not import a Pydantic schema into a
  migration.
- Keep schema and table enum values aligned with a parity test. Alembic
  migrations contain their own historical snapshot of the database values.
- `default=` is a SQLAlchemy client-side insert default. `server_default=` is a
  database default represented in DDL and Alembic. They are not interchangeable;
  choose based on who must supply the value and keep schema defaults consistent.

## Main-Branch Style and Reuse

- Follow the established structure: flat async functions, SQLAlchemy Core, thin
  controllers, existing imports, and existing response shapes.
- Keep one canonical implementation of each query, persistence operation,
  transition rule, and provider mapping. Move it to the correct layer, update all
  callers, and remove obsolete undeployed implementations rather than copying it
  or leaving a delegating shim.
- Do not mix refactors with unrelated formatting, renaming, response-envelope
  changes, or new architectural abstractions.

## Endpoint Creation Flow

When adding a resource, update each layer in order:

1. Define schemas in `schemas/<resource>.py`. Export from `schemas/__init__.py`.
2. Define SQLAlchemy table, domain exceptions, and async query functions in
   `models/<resource>.py`. Export from `models/__init__.py`.
3. Define controller functions and custom error status classes in
   `controllers/<resource>.py`. Export from `controllers/__init__.py`.
4. Define FastAPI routes in `v1/endpoints/<resources>.py`.
5. Register the router in `v1/routers.py`.
6. Change the table model first, then generate and review a Postgres migration
   under `backend/src/migrations/postgres/versions/` for any schema change.
7. Add tests under `tests/` for schemas, models, controllers, and endpoints.

## Imports

Import siblings via the parent package and access names through it:

```python
from .. import models
from .. import schemas
```

Exception: schema files must use direct sibling imports (`from . import fields`,
`from . import pagination`) because Pydantic resolves types at class definition time.

## Schemas

- Use Pydantic v2 `BaseModel`. See `backend/src/api/schemas/CLAUDE.md` for details.
- Request schemas must reject extra fields: `model_config = pydantic.ConfigDict(extra='forbid')`.
- Use `fields.Int`, `fields.String`, `fields.Dict` for bounded/strict types.

## Routes

- Routes live in `v1/endpoints/<resources>.py`.
- Every route must define: `summary`, permission dependency, `response_model`,
  `response_description`, and `responses=responses.gen_responses([...])`.
- Use `fastapi.Security(auth.get_current_user)` for authenticated routes.
- Delegate all business logic to controllers. No DB queries in route functions.
- See `backend/src/api/v1/endpoints/CLAUDE.md` for the full pattern.

## Controllers

- Controllers live in `controllers/<resource>.py`.
- Controllers never use `@postgres.session`, accept/pass database sessions, or
  open transaction scopes.
- If a use case requires several database operations to be atomic, call one
  transactional model function rather than making several independent model
  calls from the controller.
- Translate model/domain exceptions into `exceptions.HTTPBadRequestException`,
  `exceptions.HTTPNotFoundException`, or other HTTP exception types.
- Define custom bad-request statuses as `responses.Status` subclasses in the
  controller module.
- Convert create/update/upsert request schemas with
  `model_dump(mode='json', by_alias=True)` before passing data to models. Use
  the complete dumped dictionary for updates. Do not use `exclude_unset`,
  `exclude_defaults`, or `exclude_none`. Use `exclude={...}` only for fields
  handled separately by the controller and not accepted by the target table
  model.

## Models

- Use SQLAlchemy Core `sqlalchemy.Table` bound to `postgres.metadata`.
- All async functions use the `@postgres.session` decorator.
- Use SQLAlchemy statements only; do not execute raw SQL or explicit locks.
- Models own transaction scopes. An outer decorated model function passes its
  session explicitly to nested model functions when several operations must
  share one transaction.
- Prefer primitive `dict` inputs for create/update/upsert persistence functions;
  request schemas are converted in controllers. Keep typed scalar parameters for
  IDs, filters, limits, expected states, and focused database operations.
- Singular model results are plain `dict` values; collections are `list[dict]`.
  Models never construct API response schemas.
- Translate known `asyncpg` constraint errors into domain exceptions.
- See `backend/src/api/models/CLAUDE.md` for the full pattern.

## Permissions

- RBAC is defined in `backend/src/api/permission.py` via the `Perm` enum.
- Superusers (`is_superuser=True`) bypass all permission checks.
- Use `permission.PermsRequired([Perm.X])` as a route dependency.

## Migrations

- Define fields, constraints, defaults, and indexes in the SQLAlchemy table model
  first, then generate migrations with `make migration M="<description>"`.
- Use Alembic/SQLAlchemy operations only. Do not add raw SQL triggers, stored
  procedures, or schema definitions that are absent from model metadata.
- Apply the migration to a fresh development database and verify Alembic reports
  no remaining metadata drift.
- Seed data (roles, permissions) goes in the migration that creates the table,
  using `INSERT ... ON CONFLICT DO NOTHING` for idempotency.
- Every migration defines `downgrade()` with only `pass`; reverse operations are
  prohibited.
