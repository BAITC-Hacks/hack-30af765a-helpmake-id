"""Check the provider boundary without contacting an external AI service."""

import json

import httpx
import pytest

from api.controllers import simulation
from api.webhooks import advisor

from .test_simulation import EXAMPLE


@pytest.mark.parametrize(
    ('status_code', 'content', 'expected'),
    [
        (
            200,
            {
                'strengths': 'Улучшилась социальная инфраструктура Нуры.',
                'weaknesses': 'Часть районов осталась без изменений.',
                'tradeoffs': 'Средства сосредоточены на социальной сфере.',
                'remaining_critical_indicators': 'Критических показателей нет.',
            },
            'available',
        ),
        (
            200,
            {
                'strengths': 'Score вырос на 100.',
                'weaknesses': 'Нет.',
                'tradeoffs': 'Нет.',
                'remaining_critical_indicators': 'Нет.',
            },
            'unavailable',
        ),
        (503, {}, 'unavailable'),
    ],
)
async def test_provider_response_guard(monkeypatch, status_code, content, expected):
    monkeypatch.setenv('AI_API_URL', 'https://provider.example/v1/chat/completions')
    monkeypatch.setenv('AI_API_KEY', 'example-key')
    monkeypatch.setenv('AI_MODEL', 'example-model')

    def respond(request):
        assert request.headers['Authorization'] == 'Bearer example-key'
        assert json.loads(request.content)['model'] == 'example-model'
        return httpx.Response(
            status_code, json={'choices': [{'message': {'content': json.dumps(content)}}]}
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        advisor.httpx,
        'AsyncClient',
        lambda **kwargs: original(transport=httpx.MockTransport(respond)),
    )
    result = await advisor.explain(simulation.simulate(EXAMPLE))
    assert result['status'] == expected
    if expected == 'available':
        assert result['strengths'] == content['strengths']
