"""Common API schemas used across the application."""

import uuid

import pydantic


class HealthResponse(pydantic.BaseModel):
    status: str = 'ok'


class ReadyResponse(pydantic.BaseModel):
    status: str
    database: str


class ErrorResponse(pydantic.BaseModel):
    detail: str
    status: str | None = None

    model_config = pydantic.ConfigDict(extra='allow')


class UserCurrent(pydantic.BaseModel):
    """Represents the authenticated caller decoded from the JWT.

    Fields are populated from JWT claims — there is no database lookup.
    Add claim fields as your user table grows.
    """

    id: uuid.UUID
    email: pydantic.EmailStr
    is_superuser: bool = False
    permissions: list[str] = pydantic.Field(default_factory=list)

    # Optional: set when your application uses organisations / tenants
    organization_id: int | None = None

    model_config = pydantic.ConfigDict(extra='ignore')
