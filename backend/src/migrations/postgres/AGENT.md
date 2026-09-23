# PostgreSQL Migration Conventions

These instructions apply to `src/migrations/postgres/` and its `versions/`
directory. They extend `src/CLAUDE.md`.

## Source of Truth

SQLAlchemy `Table` definitions registered on `postgres.metadata` are the source
of truth for the intended application schema. Alembic migrations are the
deployment history that brings a database to that model-defined schema.

Every database field and declarative database invariant must first exist in its
table model, including:

- Columns, SQL types, and enum values.
- Nullability and server defaults.
- Primary and foreign keys, including delete/update behavior.
- Unique and check constraints.
- Ordinary, partial, expression, and dialect-specific indexes.

SQLAlchemy client-side `default=` is not database schema and therefore does not
produce an Alembic server-default operation. Only `server_default=` is database
DDL. Review this distinction explicitly instead of adding a migration default
for every model-side default.

Never add, remove, or change a field, constraint, default, or index only in a
migration. Explicitly name nontrivial constraints and indexes so generated
migrations and constraint-error translation are deterministic.

## Required Model-First Workflow

For every schema change:

1. Change the SQLAlchemy table model first.
2. Ensure the model module is imported by `src.api.models` so its table is
   registered on `postgres.metadata`.
3. Generate the migration with:

   ```shell
   make migration M="<short description>"
   ```

4. Hand-review the generated upgrade operations. Check column types,
   nullability, server defaults, enum behavior, foreign keys, constraint/index
   names, partial-index predicates, and data-preservation requirements.
5. Add data-transition operations only when existing deployed data requires
   them. Keep them deterministic and bounded.
6. Apply the full migration chain to a fresh empty development database.
7. Run Alembic's schema-drift check against the upgraded database. It must report
   that no new upgrade operations are required.
8. After the domain refactor is structurally complete, add or update automated
   model/migration tests for the schema behavior.

If autogeneration produces an empty or incomplete migration for a model change,
stop and determine why. Do not silently replace the missing operation with raw SQL.

## SQLAlchemy and Alembic Only

- Use generated Alembic operations and SQLAlchemy schema constructs only.
- Do not use `op.execute(...)` with handwritten SQL strings.
- Do not add raw DDL, PostgreSQL triggers, trigger functions, stored procedures,
  or stored functions for application behavior or persistence invariants.
- Do not add explicit locking statements or migration logic that takes broad or
  unbounded locks. Keep operations bounded and honor the configured migration
  `statement_timeout` and `lock_timeout`.
- If PostgreSQL-specific behavior cannot be represented safely with the existing
  SQLAlchemy/Alembic constructs, stop and request an explicit design decision.

Use declarative alternatives instead of procedural database code:

- `ForeignKey` / `ForeignKeyConstraint` for referential integrity.
- `UniqueConstraint` or a SQLAlchemy partial unique `Index` for uniqueness.
- `CheckConstraint` for persisted value/range invariants.
- Server defaults expressed on the model column.
- Guarded SQLAlchemy model statements for state-dependent behavior.

## Code Style

- Use single quotes and the repository's 95-character line limit.
- Put each argument of a wrapped Alembic operation, SQLAlchemy column,
  constraint, index, function call, or collection on its own line.
- End every item in a multiline call, signature, import, or collection with a
  trailing comma, including the final item.
- Put the closing parenthesis/bracket/brace on its own line at the original
  indentation level.
- Keep a short operation on one line when Ruff keeps it on one line.
- Do not manually align values with spaces or preserve formatting that Ruff
  would replace.
- Do not reformat unrelated migration history while changing one migration.

Use this pattern:

```python
def upgrade():
    op.add_column(
        'entity',
        sa.Column(
            'status',
            sa.Text(),
            nullable=False,
        ),
    )
    op.create_index(
        'ix_entity_status_created_at',
        'entity',
        [
            'status',
            'created_at',
        ],
        unique=False,
    )
```

### Native PostgreSQL enums

Finite categorical columns use the named native enum pattern from
`src/api/models/CLAUDE.md`:

```python
sa.Column(
    'status',
    postgresql.ENUM(
        'pending',
        'active',
        'completed',
        'cancelled',
        name='entity_status_enum',
    ),
    nullable=False,
    server_default='pending',
)
```

- Keep each migration self-contained: repeat the enum's stored values in the
  migration and never import a table model or application status class.
- The schema-layer `(str, enum.Enum)` and the model's native PostgreSQL enum must
  contain the same stored values. Protect current-code parity with an automated
  test; the migration intentionally retains its own historical snapshot.
- Treat the PostgreSQL enum type name as permanent schema identity. It must be
  explicit, stable, and globally unique within the database.
- Do not also create a check constraint containing the same allowed-value list.
- Changing enum members is a schema change: update the table model first,
  generate or revise the undeployed migration, and verify both a fresh upgrade
  and Alembic metadata drift.

### Defaults

- `default=` belongs to SQLAlchemy application execution and is normally absent
  from an autogenerated migration.
- `server_default=` belongs to the database schema. Generated Alembic operations
  must reproduce it exactly and schema-drift verification must remain clean.
- Pydantic schema defaults are API validation defaults and never directly
  determine Alembic output.
- When schema, SQLAlchemy client, and database defaults intentionally coexist,
  keep their values aligned.

## Migration History

- Never rewrite a migration that has been deployed to a shared or production
  database. Add a new migration for subsequent changes.
- An undeployed development migration may be regenerated or rewritten when its
  table model changes.
- Keep revision history linear unless a branch is explicitly required.
- Every migration must contain exactly this downgrade implementation:

  ```python
  def downgrade():
      pass
  ```

  Do not add reverse schema operations, reverse data migrations, helper calls,
  or conditional downgrade logic.
- Seed data belongs in the migration that creates the corresponding table and
  must be idempotent using Alembic/SQLAlchemy operations.

## Review Checklist

Before considering a migration complete, confirm:

- The table model was changed first.
- Generated migration operations match the model change and contain no unrelated
  schema churn.
- No handwritten SQL, trigger, stored procedure/function, or explicit lock was
  added.
- Constraint and index names are explicit and stable.
- A fresh empty database reaches `head` successfully.
- The upgraded schema has no Alembic metadata drift.
- Public API compatibility is preserved unless a separately approved contract
  change requires the schema change.
