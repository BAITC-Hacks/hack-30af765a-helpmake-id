# Schema Conventions

These instructions apply to Pydantic schemas in `src/api/schemas/`.

## Imports

```python
import datetime
import enum
import typing
import uuid

import pydantic

from . import fields
from . import pagination
```

Use `from . import fields` and `from . import pagination` to access siblings.

## Enums

All string enums inherit from `(str, enum.Enum)` for JSON serialization. Integer
enums use `enum.IntEnum`. Prefer a descriptive `<Name>Enum` class name for new
types unless an existing public schema name must be preserved.

The enum **value** exactly matches the external or persisted string. The Python
member name is a readable identifier and does not need to reproduce casing that
would be awkward in Python:

```python
class StatusEnum(str, enum.Enum):
    pending = 'pending'
    active = 'active'
    completed = 'completed'
    cancelled = 'cancelled'


class WorkFormatEnum(str, enum.Enum):
    ON_SITE = 'ON_SITE'
    REMOTE = 'REMOTE'
    HYBRID = 'HYBRID'
```

Shared request/response status and value enums belong in `schemas/`, not
`models/`. Table models independently list the exact stored strings in their
native PostgreSQL enum declaration, and a parity test protects the two
declarations from drift. Migrations remain self-contained historical snapshots
and never import schema enums.

## Controller Conversion Boundary

Controllers, not models, convert validated schemas for persistence:

```python
data = entity.model_dump(
    mode='json',
    by_alias=True,
)
```

- Use `mode='json'` to convert enum members and other serializable Pydantic
  values to primitive dictionary values.
- Use `by_alias=True` when aliases such as `from_ = Field(alias='from')` must be
  emitted under their external/stored name.
- Update schemas describe the complete desired mutable resource state. Do not
  use `exclude_unset`, `exclude_defaults`, or `exclude_none`.
- Use `exclude={'field_name'}` for files, nested commands, or other schema fields
  the controller handles separately and the target model must not persist.
- Schema defaults are validation/application defaults. They do not create a
  database default; table-model `default` and `server_default` have separate
  SQLAlchemy meanings and must be reviewed independently.

## Schema Hierarchy

Every entity follows this naming pattern:

| Class | Config | Purpose |
|---|---|---|
| `EntityBase` | `extra='forbid'` | Core fields |
| `EntityCreate` | inherits Base | Add relation IDs (e.g. `tag_ids`) |
| `EntityUpdate` | inherits Base | Full replacement of mutable persisted fields |
| `EntityGet` | `extra='ignore'` | Adds `id`, timestamps, nested `Get` objects |
| `EntityInternal` | `extra='ignore'` | Adds `organization_id` and internal fields |
| `EntityList` | inherits `pagination.Pagination` | Contains `list[EntityGet]` |
| `EntitySearchBody` | standalone `BaseModel` | Query body with `query: constr` field |

## Model Config

| Config | When to use |
|---|---|
| `extra='forbid'` | Create / Update / Base schemas — reject unknown fields |
| `extra='ignore'` | Get / Response / Internal schemas — tolerate extra DB columns |
| `extra='allow'` | Rare — only for flexible config objects |
| `validate_default=True` | When defaults need validation (computed/conditional) |

Always use `model_config = pydantic.ConfigDict(...)`, never the deprecated `Config` inner class.

## Field Types

Use custom types from `fields.py` instead of bare Python types:

| Custom Type | Purpose |
|---|---|
| `fields.Int` | Integer >= 1 and <= 2,147,483,647 |
| `fields.Dict` | JSON-serializable dict with size limit |

### Field Conventions

- **Strings:** `pydantic.constr(strict=True, min_length=1, max_length=255)` — always `strict=True`
- **Lists:** `pydantic.conlist(fields.Int, min_length=1, max_length=5)`
- **Booleans:** `pydantic.StrictBool` for input, plain `bool` with default for output
- **Datetimes:** `datetime.datetime` for responses, `pydantic.AwareDatetime` for timezone-aware input
- **UUIDs:** `uuid.UUID` standard
- **Optional:** `typing.Optional[Type] = None` or `Type | None = None`
- **Floats:** `pydantic.Field(allow_inf_nan=False)` on lat/lon and similar fields

## Validators

**Field validator** (single field):

```python
@pydantic.field_validator('avatar_url')
def build_avatar_url(cls, value, info):
    if info.data.get('avatar_id') is not None:
        return uploads.build_upload_url(upload_id=info.data['avatar_id'], kind='avatar')
    return None
```

**Model validator** (cross-field, post-instantiation):

```python
@pydantic.model_validator(mode='after')
def check_plan_values(self):
    if all((self.plan_x is None, self.plan_y is None, self.plan_id is None)):
        return self
    if all((self.plan_x is not None, self.plan_y is not None, self.plan_id is not None)):
        return self
    raise ValueError('Either all plan fields must be present or none')
```

**Before-model validator** (pre-instantiation transformation):

```python
@pydantic.model_validator(mode='before')
@classmethod
def validate_descriptor(cls, values):
    values = dict(values)
    # transform values...
    return values
```

## Computed Fields

For values derived from other fields:

```python
@pydantic.computed_field
@property
def is_expired(self) -> bool:
    return times.is_expired(self.updated_at)
```

## Mixins

Shared validation logic lives in `mixins.py`. Mixins are `pydantic.BaseModel` subclasses:

```python
class PeriodValidatorMixin(pydantic.BaseModel):
    min_period: typing.ClassVar[datetime.timedelta] = datetime.timedelta(hours=1)
    max_period: typing.ClassVar[datetime.timedelta] = datetime.timedelta(days=1)

    @pydantic.model_validator(mode='after')
    def ensure_period_is_valid(self):
        # validation logic...
        return self
```

Usage: `class StatsQueryParams(DateRangeValidatorMixin, PeriodValidatorMixin): ...`

## Nested Schemas & Relationships

Reference other entities via their `Get` schemas. Nested objects use `extra='ignore'`:

```python
class ParentGet(ParentBase):
    id: uuid.UUID
    created_at: datetime.datetime
    children: list[ChildGet]

    model_config = pydantic.ConfigDict(extra='ignore')
```

## Union & Literal Types

For polymorphic responses:

```python
class EventTypeA(EventBase):
    event_type: typing.Literal['type_a']
    event: EventBodyA


class EventList(pagination.Pagination):
    events: typing.List[EventTypeA | EventTypeB]
```

## Required Pattern

- Group schemas by resource in `<resource>.py`. Export from `schemas/__init__.py`.
- Use separate classes for base, create, update, get, list, search body, query
  params, and internal data when their field sets differ.
- Request schemas must reject extra fields:
  `model_config = pydantic.ConfigDict(extra='forbid')`.
- Use strict and bounded types:
  - IDs: `fields.Int`
  - strings: `typing.Annotated[str, StringConstraints(max_length=...)]`
  - response-only strings: `pydantic.StrictStr`
  - integers: `pydantic.StrictInt` or `fields.Int`
  - JSONB payloads: `fields.Dict`
- Response schemas may use `extra='ignore'` when model rows contain internal
  fields not exposed by the API.
- Do not use mutable defaults. Use `pydantic.Field(default_factory=list)`.

## Example

```python
class EntityBase(pydantic.BaseModel):
    name: typing.Annotated[str, pydantic.StringConstraints(max_length=128)]
    description: typing.Annotated[str, pydantic.StringConstraints(max_length=512)] | None = (
        None
    )


class EntityCreate(EntityBase):
    model_config = pydantic.ConfigDict(extra='forbid')


class EntityUpdate(EntityBase):
    model_config = pydantic.ConfigDict(extra='forbid')


class EntityGet(EntityBase):
    id: uuid.UUID
    is_active: pydantic.StrictBool

    model_config = pydantic.ConfigDict(extra='ignore')


class EntityList(pagination.Pagination):
    entities: list[EntityGet]
```

## Avoid

```python
class EntityCreate(pydantic.BaseModel):
    name: str
```

This accepts extra fields and does not enforce type constraints.
