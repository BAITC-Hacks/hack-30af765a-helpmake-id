"""Tests for authentication and security utilities."""

import datetime
import uuid

import jwt
import pytest

from src.core import security
from src.core.config import Settings


@pytest.fixture
def settings():
    return Settings(
        SECRET_KEY='test-secret-key-at-least-16-chars',
        DATABASE_URL='postgresql+asyncpg://x:x@localhost/db',
    )


def test_hash_password_returns_non_empty_string():
    hashed = security.hash_password('mysecret')
    assert hashed
    assert hashed != 'mysecret'


def test_verify_password_correct():
    hashed = security.hash_password('mysecret')
    assert security.verify_password('mysecret', hashed) is True


def test_verify_password_wrong():
    hashed = security.hash_password('mysecret')
    assert security.verify_password('wrong', hashed) is False


def test_verify_password_invalid_hash():
    assert security.verify_password('any', 'not-a-valid-hash') is False


def test_create_access_token_returns_string():
    token = security.create_access_token({'sub': 'user-123'})
    assert isinstance(token, str)


def test_decode_access_token_round_trip():
    data = {'sub': 'user-123', 'email': 'a@b.com'}
    token = security.create_access_token(data)
    decoded = security.decode_access_token(token)
    assert decoded['sub'] == 'user-123'
    assert decoded['email'] == 'a@b.com'


def test_decode_access_token_expired_raises():
    token = security.create_access_token(
        {'sub': 'user'},
        expires_delta=datetime.timedelta(seconds=-1),
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_access_token(token)


def test_decode_access_token_invalid_raises():
    with pytest.raises(jwt.PyJWTError):
        security.decode_access_token('not.a.token')


async def test_get_current_user_no_token(client):
    resp = await client.get('/api/v1/health')
    # /health is public so no auth needed — sanity check client works
    assert resp.status_code == 200


async def test_get_current_user_missing_token_on_protected_route():
    """A protected endpoint (if one existed) would return 401."""
    from src.api import auth, exceptions

    with pytest.raises(exceptions.HTTPUnauthorizedException):
        await auth.get_current_user(token=None)


async def test_get_current_user_invalid_token():
    from src.api import auth, exceptions

    with pytest.raises(exceptions.HTTPUnauthorizedException):
        await auth.get_current_user(token='bad.token.here')


async def test_get_current_user_valid_token():
    from src.api import auth
    from src.core import security

    user_id = uuid.uuid4()
    token = security.create_access_token(
        {
            'id': str(user_id),
            'email': 'test@example.com',
            'is_superuser': False,
        }
    )
    user = await auth.get_current_user(token=token)
    assert user.email == 'test@example.com'
    assert user.is_superuser is False


async def test_get_current_user_expired_token():
    from src.api import auth, exceptions
    from src.core import security

    token = security.create_access_token(
        {'id': str(uuid.uuid4()), 'email': 'x@x.com'},
        expires_delta=datetime.timedelta(seconds=-1),
    )
    with pytest.raises(exceptions.HTTPUnauthorizedException) as exc_info:
        await auth.get_current_user(token=token)
    assert 'expired' in exc_info.value.detail.lower()
