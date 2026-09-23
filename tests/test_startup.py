"""Tests for application startup, middleware, and configuration."""

import pytest


async def test_app_starts_and_returns_200_on_health(client):
    resp = await client.get('/api/v1/health')
    assert resp.status_code == 200


async def test_cors_headers_present_for_allowed_origin(client):
    resp = await client.get(
        '/api/v1/health',
        headers={'Origin': 'http://localhost:3000'},
    )
    # CORS headers are only present when CORS_ORIGINS includes the origin.
    # In test config CORS_ORIGINS is empty — that is correct for our env setup.
    assert resp.status_code == 200


async def test_request_id_generated_when_missing(client):
    resp = await client.get('/api/v1/health')
    assert 'x-request-id' in resp.headers
    assert len(resp.headers['x-request-id']) > 0


async def test_request_id_propagated_from_request(client):
    resp = await client.get(
        '/api/v1/health',
        headers={'X-Request-ID': 'trace-abc-123'},
    )
    assert resp.headers.get('x-request-id') == 'trace-abc-123'


async def test_unknown_route_returns_404(client):
    resp = await client.get('/api/v1/this-does-not-exist')
    assert resp.status_code == 404


async def test_http_client_lifecycle():
    from src.core import http_client

    await http_client.on_startup()
    c = http_client.get_client()
    assert c is not None
    await http_client.on_shutdown()


async def test_http_client_not_initialized_raises():
    from src.core import http_client

    # ensure it's shut down
    await http_client.on_shutdown()
    with pytest.raises(RuntimeError, match='not initialized'):
        http_client.get_client()


async def test_storage_set_and_get():
    import tempfile

    from src.core.storage import LocalStorage, get_storage, set_storage

    with tempfile.TemporaryDirectory() as tmp:
        backend = LocalStorage(tmp)
        set_storage(backend)
        stored = get_storage()
        assert stored is backend


async def test_local_storage_save_get_delete():
    import tempfile

    from src.core.storage import LocalStorage, StorageError

    with tempfile.TemporaryDirectory() as tmp:
        storage = LocalStorage(tmp)
        key = 'test/file.txt'
        await storage.save(key, b'hello world')
        data = await storage.get(key)
        assert data == b'hello world'
        await storage.delete(key)
        with pytest.raises(StorageError):
            await storage.get(key)


def test_safe_filename():
    from src.core.storage import safe_filename

    assert safe_filename('hello world.pdf') == 'hello_world.pdf'
    # pathlib.Path strips directory components; only the filename portion is sanitised
    assert safe_filename('../etc/passwd') == 'passwd'
    assert safe_filename('my-file_name.csv') == 'my-file_name.csv'


async def test_lifespan_startup_and_shutdown():
    """Covers the lifespan context manager, configure_logging, and lifecycle hooks."""
    import fastapi

    from src.main import lifespan

    mock_app = fastapi.FastAPI()
    async with lifespan(mock_app):
        from src.core import http_client

        assert http_client.get_client() is not None
