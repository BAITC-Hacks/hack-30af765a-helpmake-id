"""Bounded, strict scalar field types for Pydantic schemas.

Import via: from . import fields
"""

import typing

import pydantic

# Positive integer within PostgreSQL int4 range
Int = typing.Annotated[
    int,
    pydantic.Field(ge=1, le=2_147_483_647),
]

# Non-empty string with a sensible max length
String = typing.Annotated[
    str,
    pydantic.StringConstraints(
        strict=True,
        min_length=1,
        max_length=255,
    ),
]

# JSON-serializable dict with a size guard (approximate)
_MAX_DICT_CHARS = 65_536


def _dict_max_size(v: dict) -> dict:  # pragma: no cover
    import json

    if len(json.dumps(v)) > _MAX_DICT_CHARS:
        raise ValueError(f'Dict serialised size exceeds {_MAX_DICT_CHARS} characters')
    return v


Dict = typing.Annotated[
    dict,
    pydantic.BeforeValidator(_dict_max_size),
]
