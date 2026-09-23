"""Tests for /health and /ready endpoints."""

from unittest.mock import AsyncMock, patch


async def test_health_returns_ok(client):
    resp = await client.get('/api/v1/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}


async def test_health_has_request_id_header(client):
    resp = await client.get('/api/v1/health')
    assert 'x-request-id' in resp.headers


async def test_health_echoes_request_id(client):
    resp = await client.get('/api/v1/health', headers={'X-Request-ID': 'my-id-123'})
    assert resp.headers.get('x-request-id') == 'my-id-123'


async def test_ready_when_db_is_reachable(client):
    with patch('src.core.postgres.check_connection', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        resp = await client.get('/api/v1/ready')
    assert resp.status_code == 200
    body = resp.json()
    assert body['status'] == 'ok'
    assert body['database'] == 'reachable'


async def test_ready_when_db_is_not_reachable(client):
    with patch('src.core.postgres.check_connection', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False
        resp = await client.get('/api/v1/ready')
    assert resp.status_code == 503


async def test_health_is_public_no_auth_needed(client):
    resp = await client.get('/api/v1/health')
    assert resp.status_code == 200


async def test_docs_available(client):
    resp = await client.get('/docs')
    assert resp.status_code == 200


async def test_openapi_json_available(client):
    resp = await client.get('/openapi.json')
    assert resp.status_code == 200
    body = resp.json()
    assert 'paths' in body
    assert '/api/v1/health' in body['paths']
