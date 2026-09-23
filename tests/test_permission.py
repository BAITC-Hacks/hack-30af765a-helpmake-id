"""Tests for permission dependencies."""

import uuid

import pytest

from src.api import exceptions, permission
from src.core import security


def _make_token(is_superuser: bool = False, permissions: list[str] | None = None) -> str:
    user_id = uuid.uuid4()
    return security.create_access_token(
        {
            'id': str(user_id),
            'email': 'test@example.com',
            'is_superuser': is_superuser,
            'permissions': permissions or [],
        }
    )


async def _resolve_user(is_superuser: bool, perms: list[str] | None = None):
    from src.api import auth

    token = _make_token(is_superuser=is_superuser, permissions=perms or [])
    return await auth.get_current_user(token=token)


async def test_no_perms_required_returns_depends():
    dep = permission.NoPermsRequired()
    # dep is fastapi.Depends; invoke the inner callable directly
    await dep.dependency()


async def test_perms_required_superuser_bypasses():
    user = await _resolve_user(is_superuser=True)
    dep = permission.PermsRequired([])
    result = await dep.dependency(current_user=user)
    assert result is None


async def test_perms_required_forbidden_when_missing_perm():
    user = await _resolve_user(is_superuser=False, perms=[])

    class FakePerm(permission.Perm):
        THING_READ = 'thing:read'

    dep = permission.PermsRequired([FakePerm.THING_READ])
    with pytest.raises(exceptions.HTTPForbiddenException):
        await dep.dependency(current_user=user)


async def test_perms_required_passes_with_correct_perm():
    class FakePerm(permission.Perm):
        THING_READ = 'thing:read'

    user = await _resolve_user(is_superuser=False, perms=['thing:read'])
    dep = permission.PermsRequired([FakePerm.THING_READ])
    result = await dep.dependency(current_user=user)
    assert result is None


async def test_superuser_required_passes_for_superuser():
    user = await _resolve_user(is_superuser=True)
    dep = permission.SuperUserRequired()
    result = await dep.dependency(current_user=user)
    assert result is None


async def test_superuser_required_forbidden_for_regular_user():
    user = await _resolve_user(is_superuser=False)
    dep = permission.SuperUserRequired()
    with pytest.raises(exceptions.HTTPForbiddenException):
        await dep.dependency(current_user=user)
