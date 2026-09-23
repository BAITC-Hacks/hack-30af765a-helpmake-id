"""API schemas package.

Teams add domain schemas by creating <resource>.py files in this package
and exporting from this __init__.py.

Usage inside API layers:
    from .. import schemas         # via parent package
    schemas.UserCurrent            # common schema
    schemas.EntityCreate           # domain schema (added later)

Schema files may use direct sibling imports (from . import fields, pagination)
because Pydantic resolves types at class definition time.
"""

from .common import ErrorResponse, HealthResponse, ReadyResponse, UserCurrent
from .fields import Dict, Int, String
from .mixins import DateRangeValidatorMixin
from .pagination import Pagination

__all__ = [
    'Dict',
    'DateRangeValidatorMixin',
    'ErrorResponse',
    'HealthResponse',
    'Int',
    'Pagination',
    'ReadyResponse',
    'String',
    'UserCurrent',
]
