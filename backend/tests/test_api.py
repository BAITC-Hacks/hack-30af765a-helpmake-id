"""Exercise the public HTTP contract and AI fallback."""

import copy
import json
from pathlib import Path

import httpx

from api.controllers import simulation
from api.main import create_app

from .test_simulation import EXAMPLE


async def test_public_routes_and_request_id(client):
    health = await client.get('/api/v1/health', headers={'X-Request-ID': 'trace-123'})
    assert health.json() == {'status': 'ok'}
    assert health.headers['X-Request-ID'] == 'trace-123'
    ready = await client.get('/api/v1/ready')
    assert ready.json() == {'status': 'ok', 'dataset_version': '1.1.0'}
    assert ready.headers['X-Request-ID']
    data = await client.get('/api/v1/data')
    assert data.status_code == 200
    assert len(data.json()['districts']) == 5
    assert len(data.json()['measures']) == 14
    assert data.json()['districts'][0]['code'] == 'esil'
    assert data.json()['districts'][0]['map_anchor']['source'] == 'illustrative_manual_anchor'
    assert 'не являются' in data.json()['map_anchor_note']
    cors = await client.get('/api/v1/data', headers={'Origin': 'http://localhost:5173'})
    assert cors.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert (await client.get('/docs')).status_code == 200
    assert '/api/v1/simulate' in (await client.get('/openapi.json')).json()['paths']


async def test_live_frontend_origin_is_allowed_when_cors_is_overridden(monkeypatch):
    monkeypatch.setenv('CORS_ORIGINS', '*')
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app()),
        base_url='http://test',
    ) as client:
        frontend = await client.get(
            '/api/v1/data', headers={'Origin': 'https://helpmake-id.live'}
        )
        preflight = await client.options(
            '/api/v1/simulate',
            headers={
                'Origin': 'https://helpmake-id.live',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'content-type',
            },
        )
        unrelated = await client.get(
            '/api/v1/data', headers={'Origin': 'https://unrelated.example'}
        )
    assert frontend.headers['access-control-allow-origin'] == 'https://helpmake-id.live'
    assert preflight.status_code == 200
    assert preflight.headers['access-control-allow-origin'] == 'https://helpmake-id.live'
    assert 'POST' in preflight.headers['access-control-allow-methods']
    assert 'access-control-allow-origin' not in unrelated.headers


async def test_openapi_describes_complete_response_shapes(client):
    spec = (await client.get('/openapi.json')).json()
    published = Path(__file__).resolve().parents[2] / 'openapi.json'
    assert json.loads(published.read_text(encoding='utf-8')) == spec
    data_response = spec['paths']['/api/v1/data']['get']['responses']['200']['content'][
        'application/json'
    ]['schema']
    assert data_response['$ref'] == '#/components/schemas/DatasetResponse'
    assert (
        spec['components']['schemas']['DatasetResponse']['properties']['districts']['items'][
            '$ref'
        ]
        == '#/components/schemas/DistrictData'
    )
    result_response = spec['paths']['/api/v1/simulate']['post']['responses']['200']['content'][
        'application/json'
    ]['schema']
    assert {item['$ref'] for item in result_response['anyOf']} == {
        '#/components/schemas/SimulationSuccess',
        '#/components/schemas/SimulationFailure',
    }
    success = spec['components']['schemas']['SimulationSuccess']
    failure = spec['components']['schemas']['SimulationFailure']
    assert 'score' in success['required']
    assert 'score' not in failure['properties']
    assert success['properties']['districts']['items']['$ref'] == (
        '#/components/schemas/DistrictComparison'
    )
    assert (
        spec['components']['schemas']['AdvisorRequest']['properties']['simulation_result'][
            '$ref'
        ]
        == '#/components/schemas/SimulationSuccess'
    )
    assert success['properties']['quarters']['items']['$ref'] == (
        '#/components/schemas/QuarterResult'
    )
    assert 'district_code' in spec['components']['schemas']['QuarterDistrict']['properties']
    for path in (
        '/api/v1/advisor/recommend',
        '/api/v1/advisor/ask',
        '/api/v1/scenarios',
        '/api/v1/scenarios/compare',
        '/api/v1/scenarios/{scenario_id}',
    ):
        assert path in spec['paths']


async def test_simulation_success_and_invalid(client):
    response = await client.post('/api/v1/simulate', json={'decisions': EXAMPLE})
    assert response.status_code == 200
    body = response.json()
    assert body['score'] == 56.54
    assert body['remaining_budget'] == 5
    invalid = await client.post('/api/v1/simulate', json={'decisions': EXAMPLE[:4]})
    assert invalid.status_code == 200
    assert invalid.json()['violations'][0]['code'] == 'decision_count'
    assert 'score' not in invalid.json()
    malformed = await client.post('/api/v1/simulate', json={'decisions': [{'measure_id': 4}]})
    assert malformed.status_code == 422


async def test_advisor_unavailable_and_tamper_detection(client, monkeypatch):
    for name in (
        'AI_API_URL',
        'AI_API_KEY',
        'AI_API_KEY_1',
        'AI_API_KEY_2',
        'AI_API_KEY_3',
        'AI_MODEL',
    ):
        monkeypatch.delenv(name, raising=False)
    result = simulation.simulate(EXAMPLE)
    response = await client.post('/api/v1/advisor/explain', json={'simulation_result': result})
    assert response.status_code == 200
    assert response.json()['status'] == 'unavailable'
    legacy = copy.deepcopy(result)
    legacy.pop('quarters')
    compatible = await client.post(
        '/api/v1/advisor/explain', json={'simulation_result': legacy}
    )
    assert compatible.status_code == 200
    assert compatible.json().get('reason') != 'Simulation result is stale or altered.'
    altered = copy.deepcopy(result)
    altered['score'] = 99
    rejected = await client.post(
        '/api/v1/advisor/explain', json={'simulation_result': altered}
    )
    assert rejected.json()['reason'] == 'Simulation result is stale or altered.'
    invalid = simulation.simulate(EXAMPLE[:4])
    response = await client.post(
        '/api/v1/advisor/explain', json={'simulation_result': invalid}
    )
    assert response.status_code == 422
