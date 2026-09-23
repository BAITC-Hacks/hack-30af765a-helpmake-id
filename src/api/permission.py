"""Permission infrastructure.

RBAC is driven by the Perm enum. Superusers bypass all checks.

Usage in endpoints::

    dependencies=[permission.PermsRequired([permission.Perm.ENTITY_READ])]
    dependencies=[permission.NoPermsRequired()]
    dependencies=[permission.SuperUserRequired()]

Each function returns a fastapi.Depends() object so it can be placed directly
in the `dependencies` list without an extra Depends() wrapper.

Add permissions as domains are created::

    class Perm(enum.StrEnum):
        ENTITY_READ   = 'entity:read'
        ENTITY_CREATE = 'entity:create'
        ENTITY_UPDATE = 'entity:update'
        ENTITY_DELETE = 'entity:delete'
"""

import enum

import fastapi

from . import auth, exceptions, schemas


class Perm(enum.StrEnum):
    """All RBAC permissions.

    Add entries here when you add a new domain::

        ENTITY_READ   = 'entity:read'
        ENTITY_CREATE = 'entity:create'
    """


def NoPermsRequired() -> fastapi.params.Depends:
    """Public endpoint — no authentication required."""

    async def _check() -> None:
        pass

    return fastapi.Depends(_check)


def SuperUserRequired() -> fastapi.params.Depends:
    """Caller must be a superuser."""

    async def _check(
        current_user: schemas.UserCurrent = fastapi.Security(auth.get_current_user),  # noqa: B008
    ) -> None:
        if not current_user.is_superuser:
            raise exceptions.HTTPForbiddenException(detail='Superuser access required')

    return fastapi.Depends(_check)


def PermsRequired(
    perms: list[Perm],
    tfa_pass: bool = False,  # noqa: ARG001 — reserved for TFA passthrough
) -> fastapi.params.Depends:
    """User must hold all listed permissions (superusers bypass)."""

    async def _check(
        current_user: schemas.UserCurrent = fastapi.Security(auth.get_current_user),  # noqa: B008
    ) -> None:
        if current_user.is_superuser:
            return
        for perm in perms:
            if perm.value not in current_user.permissions:
                raise exceptions.HTTPForbiddenException()

    return fastapi.Depends(_check)
