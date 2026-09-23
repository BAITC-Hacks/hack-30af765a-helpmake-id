"""Tests for src/core/config.py."""

import pytest

from src.core.config import Settings, clear_settings_cache, get_settings


def test_get_settings_returns_settings_instance():
    s = get_settings()
    assert isinstance(s, Settings)


def test_get_settings_is_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_cors_origins_list_empty_when_not_set(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key-at-least-16-chars')
    monkeypatch.setenv('DATABASE_URL', 'postgresql+asyncpg://x:x@localhost/db')
    monkeypatch.delenv('CORS_ORIGINS', raising=False)
    clear_settings_cache()
    s = Settings(
        SECRET_KEY='test-secret-key-at-least-16-chars',
        DATABASE_URL='postgresql+asyncpg://x:x@localhost/db',
        CORS_ORIGINS='',
    )
    assert s.cors_origins_list() == []


def test_cors_origins_list_parsed():
    s = Settings(
        SECRET_KEY='test-secret-key-at-least-16-chars',
        DATABASE_URL='postgresql+asyncpg://x:x@localhost/db',
        CORS_ORIGINS='http://localhost:3000, http://localhost:5173',
    )
    assert s.cors_origins_list() == ['http://localhost:3000', 'http://localhost:5173']


def test_secret_key_too_short_raises():
    with pytest.raises(Exception, match='SECRET_KEY'):  # noqa: B017
        Settings(
            SECRET_KEY='short',
            DATABASE_URL='postgresql+asyncpg://x:x@localhost/db',
        )


def test_database_url_str():
    s = Settings(
        SECRET_KEY='test-secret-key-at-least-16-chars',
        DATABASE_URL='postgresql+asyncpg://user:pass@host/db',
    )
    assert s.database_url_str() == 'postgresql+asyncpg://user:pass@host/db'


def test_max_upload_bytes():
    s = Settings(
        SECRET_KEY='test-secret-key-at-least-16-chars',
        DATABASE_URL='postgresql+asyncpg://x:x@localhost/db',
        MAX_UPLOAD_SIZE_MB=5,
    )
    assert s.max_upload_bytes == 5 * 1024 * 1024


def test_is_production_false_by_default():
    s = Settings(
        SECRET_KEY='test-secret-key-at-least-16-chars',
        DATABASE_URL='postgresql+asyncpg://x:x@localhost/db',
    )
    assert s.is_production is False


def test_is_production_true_when_env_is_production():
    s = Settings(
        SECRET_KEY='test-secret-key-at-least-16-chars',
        DATABASE_URL='postgresql+asyncpg://x:x@localhost/db',
        APP_ENV='production',
    )
    assert s.is_production is True
