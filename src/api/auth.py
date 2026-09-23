"""Authentication dependency.

get_current_user decodes the Bearer token into a UserCurrent schema.
There is no database lookup — all user context comes from JWT claims.

When you add a user table, you can upgrade this function to verify the
user still exists and load additional fields.
"""

import fastapi
import fastapi.security
import jwt as pyjwt

from . import exceptions, schemas

_oauth2 = fastapi.security.OAuth2PasswordBearer(
    tokenUrl='/api/v1/auth/token',
    auto_error=False,
)


async def get_current_user(
    token: str | None = fastapi.Depends(_oauth2),
) -> schemas.UserCurrent:
    """Resolve the authenticated user from the Bearer token.

    Raises 401 when the token is missing or invalid.
    """
    if token is None:
        raise exceptions.HTTPUnauthorizedException(detail='Missing authentication token')

    from src.core import security

    try:
        payload = security.decode_access_token(token)
    except pyjwt.ExpiredSignatureError as exc:
        raise exceptions.HTTPUnauthorizedException(detail='Token has expired') from exc
    except pyjwt.PyJWTError as exc:
        raise exceptions.HTTPUnauthorizedException(
            detail='Invalid authentication token'
        ) from exc

    try:
        return schemas.UserCurrent(**payload)
    except Exception as exc:
        raise exceptions.HTTPUnauthorizedException(detail='Invalid token claims') from exc
