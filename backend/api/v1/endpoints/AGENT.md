# Endpoint Conventions

These instructions apply to FastAPI route modules in `src/api/v1/endpoints/`.

## File Structure

Each domain has its own file with a local router and these standard imports:

```python
import fastapi

from ... import controllers
from ... import pagination
from ... import permission
from ... import responses
from ... import schemas
from ... import auth

router = fastapi.APIRouter()
```

## Required Pattern

- Each resource module defines `router = fastapi.APIRouter(prefix='/<resources>')`.
- Every route must include:
  - `summary`
  - `dependencies=[permission.PermsRequired([...])]`
  - `response_model` when a body is returned
  - `response_description`
  - `responses=responses.gen_responses([...])` for documented non-default errors
  - `current_user: schemas.UserCurrent = fastapi.Security(auth.get_current_user)`
    unless the endpoint is intentionally public
- Route function names must be unique (used as OpenAPI operation IDs).
- Keep route functions thin — delegate all logic to controllers.
- After adding a module, register it in `src/api/v1/routers.py`.

## Permission Guards (MANDATORY)

**Every endpoint must have exactly one permission guard** in `dependencies`.

```python
# Require specific permissions (superusers bypass)
dependencies = [permission.PermsRequired([permission.Perm.ENTITY_READ])]

# With TFA passthrough
dependencies = [permission.PermsRequired([permission.Perm.USER_ME_READ], tfa_pass=True)]

# Public endpoint (no auth required)
dependencies = [permission.NoPermsRequired()]

# Superuser only
dependencies = [permission.SuperUserRequired()]
```

## Function Parameter Order

```python
async def endpoint(
    # 1. Body / file parameters
    entity: schemas.EntityCreate,
    upload_data: bytes = fastapi.File(...),

    # 2. Path parameters (auto-extracted)
    entity_id: uuid.UUID,

    # 3. Query parameters
    place_id: schemas.Int | None = None,
    group_id: list[schemas.Int] = fastapi.Query(None),

    # 4. Auth dependencies
    current_user: schemas.UserCurrent = fastapi.Security(auth.get_current_user),

    # 5. Other dependencies
    request: fastapi.Request,
    background_tasks: fastapi.BackgroundTasks,
    paginator=pagination.Paginator(pagination.EntityType.ENTITY_LIST),
):
```

## Pagination

List endpoints inject a `Paginator` with an `EntityType`:

```python
@router.get('/entities')
async def list_entities(
    query_params: schemas.EntityListQueryParams = fastapi.Depends(),
    paginator: pagination.Paginator = fastapi.Depends(
        pagination.Paginator(pagination.EntityType.ENTITY_LIST),
    ),
    current_user: schemas.UserCurrent = fastapi.Security(auth.get_current_user),
):
    return await controllers.entity_list(paginator, query_params)
```

Search endpoints use a separate `EntityType` and accept a body:

```python
@router.post('/entities/search')
async def search_entities(
    search: schemas.EntitySearchBody,
    paginator=pagination.Paginator(pagination.EntityType.ENTITY_SEARCH),
    current_user: schemas.UserCurrent = fastapi.Security(auth.get_current_user),
):
    return await controllers.entity_search(paginator, current_user, search_body=search)
```

## Delete Endpoints

```python
@router.delete(
    '/entities/{entity_id}',
    summary='Delete an entity',
    dependencies=[permission.PermsRequired([permission.Perm.ENTITY_DELETE])],
    status_code=204,
    response_class=fastapi.Response,
    responses=responses.gen_responses(
        [
            responses.APIResponseNotFound,
            controllers.EntityDeleteAPIResponseBadRequest,
        ]
    ),
)
async def delete_entity(
    entity_id: uuid.UUID,
    current_user: schemas.UserCurrent = fastapi.Security(auth.get_current_user),
):
    await controllers.entity_delete(current_user, entity_id)
```

## Docstrings

Document error responses in the docstring:

```python
async def create_entity(...):
    """Create a new entity.

    Returns 400 BAD REQUEST in the following cases:

    * `entity_name_already_in_use` - An entity with this name already exists
    """
```

## Example

```python
router = fastapi.APIRouter(prefix='/entities')


@router.get(
    '/',
    summary='List entities',
    dependencies=[permission.PermsRequired([permission.Perm.ENTITY_READ])],
    response_model=schemas.EntityList,
    response_description='List of entities',
    responses=responses.gen_responses([]),
)
async def list_entities(
    query_params: schemas.EntityListQueryParams = fastapi.Depends(),
    paginator: pagination.Paginator = fastapi.Depends(
        pagination.Paginator(pagination.EntityType.ENTITY_LIST),
    ),
    current_user: schemas.UserCurrent = fastapi.Security(auth.get_current_user),
):
    """List entities with optional filters."""
    return await controllers.entity_list(paginator, query_params)


@router.post(
    '/',
    summary='Create an entity',
    dependencies=[permission.PermsRequired([permission.Perm.ENTITY_CREATE])],
    response_model=schemas.EntityGet,
    response_description='Created entity',
    responses=responses.gen_responses([controllers.EntityCreateAPIResponseBadRequest]),
)
async def create_entity(
    entity: schemas.EntityCreate,
    current_user: schemas.UserCurrent = fastapi.Security(auth.get_current_user),
):
    """Create a new entity.

    Returns 400 BAD REQUEST in the following cases:

    * `entity_name_already_in_use` - An entity with this name already exists
    """
    return await controllers.entity_create(current_user, entity=entity)
```

## Router Registration

In `v1/routers.py`, register with tags inside `get_routers()`:

```python
router.include_router(entities.router, tags=['Entities'])
router.include_router(users.router, tags=['Users'])
```

## Avoid

```python
@router.post('/entities')
async def create_entity(entity: dict):
    return await models.entity_create(entity)
```

This bypasses schema validation, permissions, auth, OpenAPI docs, and controller
exception mapping. Route handlers must only extract and forward parameters to
the controller — never contain business logic, DB calls, or exception handling.
