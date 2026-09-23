"""Durable scenario CRUD and deterministic comparison."""

import copy

import sqlalchemy as sa

from api.controllers import simulation
from api.models import scenario as store

from .test_simulation import EXAMPLE, decision

ALTERNATIVE = [*EXAMPLE[:4], decision('M6')]


async def test_save_list_get_compare_delete_and_reopen(client, monkeypatch, tmp_path):
    path = tmp_path / 'scenarios.sqlite3'
    monkeypatch.setenv('SCENARIO_DB_PATH', str(path))
    left_response = await client.post(
        '/api/v1/scenarios', json={'name': 'Исходный план', 'decisions': EXAMPLE}
    )
    right_response = await client.post(
        '/api/v1/scenarios', json={'name': 'Другой план', 'decisions': ALTERNATIVE}
    )
    assert left_response.status_code == right_response.status_code == 201
    left = left_response.json()
    right = right_response.json()
    assert path.is_file()
    assert left['result'] == simulation.simulate(EXAMPLE)
    assert left['dataset_hash'] == left['result']['dataset_hash']
    assert left['created_at']
    listing = await client.get('/api/v1/scenarios')
    assert [item['id'] for item in listing.json()] == [right['id'], left['id']]
    assert all('result' not in item for item in listing.json())

    comparison = await client.post(
        '/api/v1/scenarios/compare',
        json={'left_id': left['id'], 'right_id': right['id']},
    )
    assert comparison.status_code == 200
    body = comparison.json()
    assert body['score_delta'] == round(right['score'] - left['score'], 2)
    assert body['spent_delta'] == right['spent'] - left['spent']
    assert body['remaining_budget_delta'] == -body['spent_delta']
    saryarka = next(item for item in body['districts'] if item['district_code'] == 'saryarka')
    assert saryarka['indicator_deltas']['E1'] > 0
    assert body['critical_pairs_left'] == left['result']['critical_pairs_after']

    store._engine(str(path)).dispose()
    store._engine.cache_clear()
    store._schema_ready.discard(str(path))
    reopened = await client.get(f'/api/v1/scenarios/{left["id"]}')
    assert reopened.status_code == 200
    assert reopened.json()['result'] == left['result']
    deleted = await client.delete(f'/api/v1/scenarios/{left["id"]}')
    assert deleted.status_code == 204
    assert (await client.get(f'/api/v1/scenarios/{left["id"]}')).status_code == 404
    assert (await client.delete(f'/api/v1/scenarios/{left["id"]}')).status_code == 404


async def test_invalid_scenario_is_never_saved(client, monkeypatch, tmp_path):
    monkeypatch.setenv('SCENARIO_DB_PATH', str(tmp_path / 'invalid.sqlite3'))
    response = await client.post(
        '/api/v1/scenarios', json={'name': 'Bad', 'decisions': EXAMPLE[:4]}
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['code'] == 'decision_count'
    assert (await client.get('/api/v1/scenarios')).json() == []


async def test_compare_rejects_different_dataset_versions(client, monkeypatch, tmp_path):
    monkeypatch.setenv('SCENARIO_DB_PATH', str(tmp_path / 'versions.sqlite3'))
    current = (
        await client.post('/api/v1/scenarios', json={'name': 'Current', 'decisions': EXAMPLE})
    ).json()
    old_result = copy.deepcopy(current['result'])
    old_result['dataset_version'] = '0.9.0'
    old_result['dataset_hash'] = '0' * 64
    old = await store.create(
        {
            'name': 'Old',
            'decisions': old_result['decisions'],
            'dataset_version': old_result['dataset_version'],
            'dataset_hash': old_result['dataset_hash'],
            'result': old_result,
            'score': old_result['score'],
            'spent': old_result['spent'],
            'budget': old_result['budget'],
        }
    )
    response = await client.post(
        '/api/v1/scenarios/compare',
        json={'left_id': current['id'], 'right_id': old['id']},
    )
    assert response.status_code == 409
    assert 'different dataset' in response.json()['detail']


async def test_readiness_reports_unavailable_storage(client, monkeypatch):
    async def broken_storage():
        raise RuntimeError('Storage unavailable')

    monkeypatch.setattr(store, 'ready', broken_storage)
    response = await client.get('/api/v1/ready')
    assert response.status_code == 503
    assert response.json()['detail'] == 'Scenario storage unavailable.'


async def test_unknown_storage_schema_version_is_rejected(client, monkeypatch, tmp_path):
    path = tmp_path / 'future.sqlite3'
    monkeypatch.setenv('SCENARIO_DB_PATH', str(path))
    assert (await client.get('/api/v1/ready')).status_code == 200
    engine = store._engine(str(path))
    with engine.begin() as connection:
        connection.execute(sa.update(store.SchemaVersion).values(version=2))
    store._schema_ready.discard(str(path))
    response = await client.get('/api/v1/ready')
    assert response.status_code == 503
    assert response.json()['detail'] == 'Scenario storage unavailable.'
