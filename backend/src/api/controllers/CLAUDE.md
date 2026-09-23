# Controller Conventions

These instructions apply to controller modules in `src/api/controllers/`.

Controllers are the single home for a business use case. See `src/api/CLAUDE.md`
for the full layer contract.

## Responsibilities

Controllers own:

- Business validation and rules.
- State-machine policy and selection of the intended transition.
- Use-case orchestration that does not carry database context across model calls.
- Internal business outcome selection. Request/response value enums that
  participate in API validation belong in `schemas/`.
- Orchestration used by **routes, webhooks, CLI, and scheduled services** — not
  just HTTP routes.
- Converting validated Pydantic command/request schemas into primitive
  dictionaries before persistence.
- Enriching persistence dictionaries with business-derived values such as the
  current organization, actor identity, or output from an external adapter.

All reusable custom domain and persistence exception classes belong in the
relevant `models/<domain>.py` module and are exported from `models/__init__.py`.
Controllers may raise, catch, and translate those model-owned exceptions, but
must not declare their own custom domain exception classes.

## Boundaries

- Controllers call **model** functions for all persistence.
- Controllers never use `@postgres.session`, accept a `session` argument, pass
  sessions between functions, or open `session.transaction()`.
- Controllers must not construct SQLAlchemy statements
  (`Table.select/insert/update`, `sqlalchemy.select`, …) or call
  `session.fetch_*` / `session.execute`.
- Controllers do not import `postgres` for database access or transaction
  management.
- Business decisions (why/when a DB operation happens) live here; executing or
  constructing the operation lives in `models/`.
- Provider request/response handling and outbound HTTP belong in `webhooks/`,
  not controllers.
- A controller may orchestrate an external adapter call, but it must not
  implement the HTTP client itself and must never hold a model/database
  transaction open across that call.

## Schema Input and Model Dictionaries

Create, update, and upsert controllers receive Pydantic schemas at the boundary.
Convert them before calling the model:

```python
async def entity_create(
    entity: schemas.EntityCreate,
    current_user: schemas.UserCurrent,
) -> dict:
    data = entity.model_dump(
        mode='json',
        by_alias=True,
    )
    data['organization_id'] = current_user.organization_id
    return await models.entity_create(data)
```

- Use `mode='json'` so `(str, enum.Enum)` members and other Pydantic values are
  converted to primitive persistence values.
- Use `by_alias=True` when aliases define stored or provider-facing keys.
- Updates are full replacements. Dump the complete validated update schema and
  do not use `exclude_unset`, `exclude_defaults`, or `exclude_none` to create a
  sparse update dictionary.
- Use `exclude={'field_name'}` when a schema contains values that are not columns
  of the target table or must be processed separately (e.g. uploaded files,
  nested child commands, transport-only metadata).
- Add controller-owned/business-derived fields after dumping the schema.
- Do not wrap scalar lookup and operation arguments in arbitrary dictionaries.
  IDs, filters, limits, expected versions/statuses remain explicit typed arguments.

For an update, pass the whole schema-derived dictionary:

```python
async def entity_update(
    entity_id: int,
    entity: schemas.EntityUpdate,
    current_user: schemas.UserCurrent,
) -> dict:
    data = entity.model_dump(
        mode='json',
        by_alias=True,
    )
    data['organization_id'] = current_user.organization_id
    return await models.entity_update(entity_id, data)
```

## Atomic Persistence Workflows

Calling several decorated model functions from a controller does **not** create
one unit of work. When several reads/writes must commit atomically, expose one
outer model function that owns the transaction and composes the required model
operations using its session.

The controller selects the intended action and supplies policy inputs. The model
uses constraints and guarded SQLAlchemy statements to re-check expected database
state, applies the changes atomically, and returns a plain dictionary containing
facts such as `applied`, `stale`, `not_found`, or the persisted status. The
controller maps those facts to the business outcome.

```python
# controller: no postgres import, session, or transaction
async def event_skip(event_id, actor, reason):
    allowed_statuses = ...
    result = await models.event_skip_apply(
        event_id,
        actor,
        reason,
        allowed_statuses=allowed_statuses,
    )
    if result['status'] == 'not_allowed':
        raise EventActionNotAllowed
    return result
```

## Results and Reuse

- Controllers receive plain `dict` or `list[dict]` values from models and return
  plain dictionaries to routes.
- Do not instantiate response schemas merely to convert a database row.
- Keep one implementation of each business rule. Move it into the controller,
  update every route/webhook/CLI/service caller, and remove obsolete undeployed
  implementations.
- Preserve documented routes, fields, HTTP/error behavior, and webhook contracts
  while refactoring internals.

## HTTP Error Mapping

When a controller is invoked from an HTTP route:

- Translate model/domain exceptions into existing HTTP exceptions. Do not expose
  raw database or internal exception details to clients.
- Define expected bad-request statuses as `responses.Status` subclasses in the
  controller module.
- Define matching `responses.APIResponseBadRequest` subclasses so routes can
  document custom 400 responses with `responses.gen_responses(...)`.

## Example

```python
class EntityCreateBadRequestStatus(responses.Status):
    ENTITY_NAME_ALREADY_IN_USE = 'entity_name_already_in_use'


class EntityCreateAPIResponseBadRequest(responses.APIResponseBadRequest):
    status: EntityCreateBadRequestStatus


async def entity_create(
    current_user: schemas.UserCurrent,
    entity: schemas.EntityCreate,
) -> dict:
    data = entity.model_dump(
        mode='json',
        by_alias=True,
    )
    data['organization_id'] = current_user.organization_id
    try:
        return await models.entity_create(data)
    except models.EntityNameAlreadyInUse:
        raise exceptions.HTTPBadRequestException(
            detail='An entity with this name already exists',
            status=EntityCreateBadRequestStatus.ENTITY_NAME_ALREADY_IN_USE,
        )
```

## Avoid

```python
async def entity_create(current_user, entity):
    return await models.entity_create(entity=entity)
```

This passes a Pydantic request object into the model and lets model exceptions
leak beyond the controller boundary.
