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
    for name in ('AI_API_KEY_1', 'AI_API_KEY_2', 'AI_API_KEY_3'):
        monkeypatch.delenv(name, raising=False)
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


async def test_provider_uses_third_key_after_quota_responses(monkeypatch):
    monkeypatch.setenv('AI_API_URL', 'https://provider.example/v1/chat/completions')
    monkeypatch.setenv('AI_MODEL', 'example-model')
    monkeypatch.setenv('AI_API_KEY', 'legacy-key')
    monkeypatch.setenv('AI_API_KEY_1', 'first-key')
    monkeypatch.setenv('AI_API_KEY_2', 'second-key')
    monkeypatch.setenv('AI_API_KEY_3', 'third-key')
    attempted = []

    def respond(request):
        attempted.append(request.headers['Authorization'])
        if len(attempted) < 3:
            return httpx.Response(429)
        return httpx.Response(
            200,
            json={'choices': [{'message': {'content': json.dumps({'answer': 'Готово.'})}}]},
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        advisor.httpx,
        'AsyncClient',
        lambda **kwargs: original(transport=httpx.MockTransport(respond)),
    )
    assert await advisor._call_provider('Prompt', {'fact': 'value'}) == {'answer': 'Готово.'}
    assert attempted == ['Bearer first-key', 'Bearer second-key', 'Bearer third-key']


async def test_provider_does_not_retry_server_error_with_another_key(monkeypatch):
    monkeypatch.setenv('AI_API_URL', 'https://provider.example/v1/chat/completions')
    monkeypatch.setenv('AI_MODEL', 'example-model')
    monkeypatch.setenv('AI_API_KEY_1', 'first-key')
    monkeypatch.setenv('AI_API_KEY_2', 'second-key')
    attempted = []

    def respond(request):
        attempted.append(request.headers['Authorization'])
        return httpx.Response(500)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        advisor.httpx,
        'AsyncClient',
        lambda **kwargs: original(transport=httpx.MockTransport(respond)),
    )
    with pytest.raises(httpx.HTTPStatusError):
        await advisor._call_provider('Prompt', {'fact': 'value'})
    assert attempted == ['Bearer first-key']
