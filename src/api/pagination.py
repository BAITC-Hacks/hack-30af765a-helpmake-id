"""FastAPI pagination dependency.

Usage in endpoints::

    paginator: pagination.Paginator = fastapi.Depends(
        pagination.Paginator(pagination.EntityType.ENTITY_LIST),
    ),

Then pass paginator.limit and paginator.offset to the model list function.

Add entity types when you add new domains::

    class EntityType(str, enum.Enum):
        ENTITY_LIST   = 'entity_list'
        ENTITY_SEARCH = 'entity_search'
"""

import enum

import fastapi

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class EntityType(enum.StrEnum):
    """Pagination entity types.

    Add one entry per list/search endpoint when you create a new domain::

        ENTITY_LIST   = 'entity_list'
        ENTITY_SEARCH = 'entity_search'
    """


class Paginator:
    """FastAPI dependency that extracts and validates limit/offset query params.

    Each request gets a fresh Paginator instance so there is no shared state.
    """

    def __init__(
        self,
        entity_type: EntityType | None = None,
    ) -> None:
        self.entity_type = entity_type
        self.limit: int = DEFAULT_LIMIT
        self.offset: int = 0

    async def __call__(
        self,
        limit: int = fastapi.Query(
            default=DEFAULT_LIMIT,
            ge=1,
            le=MAX_LIMIT,
            description='Number of records to return',
        ),
        offset: int = fastapi.Query(
            default=0,
            ge=0,
            description='Number of records to skip',
        ),
    ) -> 'Paginator':
        p = Paginator(self.entity_type)
        p.limit = limit
        p.offset = offset
        return p
