import datetime
import typing

import bcrypt
import jwt

from . import config


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(
    data: dict[str, typing.Any],
    expires_delta: datetime.timedelta | None = None,
) -> str:
    settings = config.get_settings()
    payload = dict(data)
    now = datetime.datetime.now(datetime.UTC)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload['exp'] = expire
    payload['iat'] = now
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def decode_access_token(token: str) -> dict[str, typing.Any]:
    settings = config.get_settings()
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=['HS256'],
    )
