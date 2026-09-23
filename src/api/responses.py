"""Response helpers for FastAPI route documentation and error formatting."""

import enum
import typing

import pydantic


class Status(enum.StrEnum):
    """Base class for bad-request status string enums.

    Usage::

        class EntityCreateBadRequestStatus(responses.Status):
            ENTITY_NAME_ALREADY_IN_USE = 'entity_name_already_in_use'
    """


class APIResponse(pydantic.BaseModel):
    """Base class for documented API response schemas."""

    detail: str

    model_config = pydantic.ConfigDict(extra='ignore')

    @classmethod
    def status_code(cls) -> int:  # pragma: no cover
        return 200

    @classmethod
    def description(cls) -> str:  # pragma: no cover
        return cls.__doc__ or 'Response'


class APIResponseBadRequest(APIResponse):
    """400 Bad Request."""

    status: str

    @classmethod
    def status_code(cls) -> int:
        return 400

    @classmethod
    def description(cls) -> str:
        return cls.__doc__ or 'Bad request'


class APIResponseUnauthorized(APIResponse):
    """401 Unauthorized."""

    @classmethod
    def status_code(cls) -> int:
        return 401


class APIResponseForbidden(APIResponse):
    """403 Forbidden."""

    @classmethod
    def status_code(cls) -> int:
        return 403


class APIResponseNotFound(APIResponse):
    """404 Not found."""

    @classmethod
    def status_code(cls) -> int:
        return 404


class APIResponseConflict(APIResponse):
    """409 Conflict."""

    @classmethod
    def status_code(cls) -> int:
        return 409


class APIResponseInternalServerError(APIResponse):
    """500 Internal server error."""

    @classmethod
    def status_code(cls) -> int:
        return 500


ResponseClass = typing.TypeVar('ResponseClass', bound=type[APIResponse])


def gen_responses(
    response_classes: list[type[APIResponse]],
) -> dict[int, dict[str, typing.Any]]:
    """Generate the OpenAPI `responses` dict from a list of response schema classes."""
    result: dict[int, dict[str, typing.Any]] = {}
    for cls in response_classes:
        code = cls.status_code()
        result[code] = {
            'model': cls,
            'description': cls.description(),
        }
    return result
