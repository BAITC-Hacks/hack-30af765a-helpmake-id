"""Tests for schemas, pagination, and field types."""

import uuid

import pydantic
import pytest

from src.api import schemas
from src.api.pagination import DEFAULT_LIMIT, Paginator
from src.api.schemas import fields

# ── fields ────────────────────────────────────────────────────────────────────


def test_int_field_accepts_valid():
    class M(pydantic.BaseModel):
        v: fields.Int

    assert M(v=1).v == 1
    assert M(v=2_147_483_647).v == 2_147_483_647


def test_int_field_rejects_zero():
    class M(pydantic.BaseModel):
        v: fields.Int

    with pytest.raises(pydantic.ValidationError):
        M(v=0)


def test_string_field_accepts_valid():
    class M(pydantic.BaseModel):
        v: fields.String

    assert M(v='hello').v == 'hello'


def test_string_field_rejects_empty():
    class M(pydantic.BaseModel):
        v: fields.String

    with pytest.raises(pydantic.ValidationError):
        M(v='')


# ── UserCurrent ───────────────────────────────────────────────────────────────


def test_user_current_defaults():
    u = schemas.UserCurrent(
        id=uuid.uuid4(),
        email='user@example.com',
    )
    assert u.is_superuser is False
    assert u.permissions == []
    assert u.organization_id is None


def test_user_current_ignores_extra_fields():
    u = schemas.UserCurrent(
        id=str(uuid.uuid4()),
        email='user@example.com',
        unknown_field='ignored',
    )
    assert u.email == 'user@example.com'


# ── Pagination schema ─────────────────────────────────────────────────────────


def test_pagination_schema_valid():
    p = schemas.Pagination(total=100, limit=20, offset=0)
    assert p.total == 100


# ── Paginator dependency ──────────────────────────────────────────────────────


async def test_paginator_defaults():
    paginator = Paginator()
    result = await paginator(limit=DEFAULT_LIMIT, offset=0)
    assert result.limit == DEFAULT_LIMIT
    assert result.offset == 0


async def test_paginator_custom_values():
    paginator = Paginator()
    result = await paginator(limit=50, offset=10)
    assert result.limit == 50
    assert result.offset == 10


async def test_paginator_creates_fresh_instance_per_call():
    paginator = Paginator()
    r1 = await paginator(limit=10, offset=0)
    r2 = await paginator(limit=20, offset=5)
    assert r1 is not r2
    assert r1.limit == 10
    assert r2.limit == 20


# ── HealthResponse / ReadyResponse ────────────────────────────────────────────


def test_health_response_default():
    h = schemas.HealthResponse()
    assert h.status == 'ok'


def test_ready_response():
    r = schemas.ReadyResponse(status='ok', database='reachable')
    assert r.database == 'reachable'


# ── DateRangeValidatorMixin ───────────────────────────────────────────────────


def test_date_range_mixin_valid():
    import datetime

    from src.api.schemas.mixins import DateRangeValidatorMixin

    class Q(DateRangeValidatorMixin):
        pass

    q = Q(
        start_date=datetime.date(2024, 1, 1),
        end_date=datetime.date(2024, 12, 31),
    )
    assert q.start_date < q.end_date


def test_date_range_mixin_invalid():
    import datetime

    from src.api.schemas.mixins import DateRangeValidatorMixin

    class Q(DateRangeValidatorMixin):
        pass

    with pytest.raises(pydantic.ValidationError):
        Q(
            start_date=datetime.date(2024, 12, 31),
            end_date=datetime.date(2024, 1, 1),
        )
