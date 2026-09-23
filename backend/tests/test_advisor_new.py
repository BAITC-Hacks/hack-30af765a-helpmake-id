"""Grounded recommendations and question answering at the public boundary."""

import copy

import httpx
import pytest

from api.controllers import advisor, dataset, simulation, validator
from api.webhooks import advisor as provider

from .test_simulation import EXAMPLE


def _configured(monkeypatch):
    monkeypatch.setenv('AI_API_URL', 'https://provider.example/v1/chat/completions')
    monkeypatch.setenv('AI_API_KEY', 'test-key')
    monkeypatch.setenv('AI_MODEL', 'test-model')


async def test_new_advisor_routes_return_explicit_fallback(client, monkeypatch):
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
    recommendation = await client.post(
        '/api/v1/advisor/recommend',
        json={'simulation_result': result, 'goal': 'balanced'},
    )
    answer = await client.post(
        '/api/v1/advisor/ask',
        json={'simulation_result': result, 'question': 'Почему вырос Score?'},
    )
    assert recommendation.status_code == answer.status_code == 200
    assert recommendation.json()['status'] == answer.json()['status'] == 'unavailable'
    assert simulation.simulate(EXAMPLE)['score'] == result['score']


@pytest.mark.parametrize('question', ['', '   ', 'x' * 1001, 42])
async def test_ask_rejects_empty_oversized_or_wrong_type(client, question):
    response = await client.post(
        '/api/v1/advisor/ask',
        json={'simulation_result': simulation.simulate(EXAMPLE), 'question': question},
    )
    assert response.status_code == 422
    assert response.json()['detail']


async def test_recommendations_are_recalculated_and_respect_constraints(client, monkeypatch):
    _configured(monkeypatch)
    result = simulation.simulate(EXAMPLE)

    async def choose_first(prompt, facts):
        assert facts['goal'] == 'balanced'
        assert facts['candidates']
        return {'candidate_ids': ['C1']}

    monkeypatch.setattr(provider, '_call_provider', choose_first)
    response = await client.post(
        '/api/v1/advisor/recommend',
        json={
            'simulation_result': result,
            'goal': 'balanced',
            'constraints': {'locked_measure_ids': ['M12'], 'max_spent': 100},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'available'
    assert body['recommendations']
    item = body['recommendations'][0]
    assert len(item['decisions']) == 5
    assert any(decision['measure_id'] == 'M12' for decision in item['decisions'])
    assert validator.validate(item['decisions'], dataset.load_dataset())[0] == []
    calculated = simulation.simulate(item['decisions'])
    assert item['score'] == calculated['score']
    assert item['score_delta'] == round(calculated['score'] - result['score'], 2)
    assert item['spent'] <= 100
    assert f'{item["score_delta"]:+.2f}' in item['tradeoff']


async def test_recommendation_rejects_unknown_candidate_and_bad_constraints(
    client, monkeypatch
):
    _configured(monkeypatch)

    async def invent_candidate(prompt, facts):
        return {'candidate_ids': ['C999']}

    monkeypatch.setattr(provider, '_call_provider', invent_candidate)
    result = simulation.simulate(EXAMPLE)
    response = await client.post(
        '/api/v1/advisor/recommend',
        json={'simulation_result': result, 'goal': 'transport'},
    )
    assert response.json()['status'] == 'unavailable'
    bad = await client.post(
        '/api/v1/advisor/recommend',
        json={
            'simulation_result': result,
            'goal': 'transport',
            'constraints': {'locked_measure_ids': ['M99']},
        },
    )
    assert bad.status_code == 422
    conflict = await client.post(
        '/api/v1/advisor/recommend',
        json={
            'simulation_result': result,
            'goal': 'transport',
            'constraints': {
                'locked_measure_ids': ['M12'],
                'excluded_measure_ids': ['M12'],
            },
        },
    )
    assert conflict.status_code == 422


async def test_recommendation_drops_invalid_provider_selection(client, monkeypatch):
    _configured(monkeypatch)
    result = simulation.simulate(EXAMPLE)

    async def invalid_choice(*args):
        return {
            'status': 'available',
            'recommendations': [{'decisions': EXAMPLE[:4], 'tradeoff': 'Неверный набор.'}],
        }

    monkeypatch.setattr(provider, 'recommend', invalid_choice)
    response = await client.post(
        '/api/v1/advisor/recommend',
        json={'simulation_result': result, 'goal': 'balanced'},
    )
    assert response.json() == {'status': 'available', 'recommendations': []}


async def test_recommendation_respects_spending_cap(client, monkeypatch):
    _configured(monkeypatch)
    response = await client.post(
        '/api/v1/advisor/recommend',
        json={
            'simulation_result': simulation.simulate(EXAMPLE),
            'goal': 'balanced',
            'constraints': {'max_spent': 60},
        },
    )
    assert response.json() == {'status': 'available', 'recommendations': []}


def test_target_district_changes_direction_goal():
    result = simulation.simulate(EXAMPLE)
    source = dataset.load_dataset()
    city = advisor._goal_value(result, 'transport', source, None)
    nura = advisor._goal_value(result, 'transport', source, 'nura')
    assert city != nura


async def test_ask_accepts_grounded_text_and_rejects_fabricated_numbers(client, monkeypatch):
    _configured(monkeypatch)
    result = simulation.simulate(EXAMPLE)

    async def grounded(prompt, facts):
        assert str(result['score']) in facts['facts']['score']
        return {'fact_ids': ['score', 'district_nura']}

    monkeypatch.setattr(provider, '_call_provider', grounded)
    response = await client.post(
        '/api/v1/advisor/ask',
        json={'simulation_result': result, 'question': 'Почему вырос Score?'},
    )
    assert response.json()['status'] == 'available'
    assert 'Нура' in response.json()['answer']
    assert str(result['score']) in response.json()['answer']

    async def fabricated(prompt, facts):
        return {'fact_ids': ['measure_M99']}

    monkeypatch.setattr(provider, '_call_provider', fabricated)
    rejected = await client.post(
        '/api/v1/advisor/ask',
        json={'simulation_result': result, 'question': 'Почему вырос Score?'},
    )
    assert rejected.json()['status'] == 'unavailable'


async def test_new_advisor_routes_reject_stale_results(client, monkeypatch):
    _configured(monkeypatch)
    result = copy.deepcopy(simulation.simulate(EXAMPLE))
    result['score'] = 99
    recommendation = await client.post(
        '/api/v1/advisor/recommend',
        json={'simulation_result': result, 'goal': 'balanced'},
    )
    answer = await client.post(
        '/api/v1/advisor/ask',
        json={'simulation_result': result, 'question': 'Почему?'},
    )
    assert recommendation.json()['status'] == answer.json()['status'] == 'unavailable'


async def test_new_advisor_routes_handle_provider_outage(client, monkeypatch):
    _configured(monkeypatch)

    async def offline(prompt, facts):
        raise httpx.ConnectError('offline')

    monkeypatch.setattr(provider, '_call_provider', offline)
    result = simulation.simulate(EXAMPLE)
    recommendation = await client.post(
        '/api/v1/advisor/recommend',
        json={'simulation_result': result, 'goal': 'balanced'},
    )
    answer = await client.post(
        '/api/v1/advisor/ask',
        json={'simulation_result': result, 'question': 'Почему изменился Score?'},
    )
    assert recommendation.json()['status'] == answer.json()['status'] == 'unavailable'
