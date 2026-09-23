"""Test configuration and shared fixtures."""

import os

import httpx
import pytest
import pytest_asyncio

# Provide a test SECRET_KEY before any src imports happen.
os.environ.setdefault('SECRET_KEY', 'test-secret-key-that-is-long-enough-32chars')
os.environ.setdefault(
    'DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/templ'
)


from src.core.config import clear_settings_cache
from src.main import app

TEST_DATABASE_URL = os.environ.get('TEST_DATABASE_URL', '')
DB_AVAILABLE = bool(TEST_DATABASE_URL)

skip_without_db = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason='TEST_DATABASE_URL not set — skipping database tests',
)


@pytest_asyncio.fixture
async def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url='http://test',
    ) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_settings_cache():
    yield
    clear_settings_cache()
