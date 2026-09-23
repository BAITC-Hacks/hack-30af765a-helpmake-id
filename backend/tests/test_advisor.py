"""Check the provider boundary without contacting an external AI service."""

import json

import httpx
import pytest

from api.webhooks import advisor


@pytest.mark.parametrize(
    ('status_code', 'content', 'expected'),
    [
        (
            200,
            {
                'strengths': 'city_score',
                'weaknesses': 'weakest_district',
                'tradeoffs': 'budget',
                'remaining_critical_indicators': 'critical_pairs',
            },
            'available',
        ),
        (
            200,
            {
                'strengths': 'Score вырос на 100.',
                'weaknesses': 'weakest_district',
                'tradeoffs': 'budget',
                'remaining_critical_indicators': 'critical_pairs',
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

    evidence = {
        'strengths': {'city_score': 'Score вырос с 52.56 до 56.54.'},
        'weaknesses': {'weakest_district': 'Слабейший район — Нура.'},
        'tradeoffs': {'budget': 'Потрачено 95 из 100.'},
        'remaining_critical_indicators': {
            'critical_pairs': 'Критические показатели Нуры — S1 и S2.',
        },
    }

    def respond(request):
        assert request.headers['Authorization'] == 'Bearer example-key'
        assert json.loads(request.content)['model'] == 'example-model'
        assert json.loads(request.content)['messages'][1]['content'] == json.dumps(
            {'evidence': evidence}, ensure_ascii=False
        )
        return httpx.Response(
            status_code, json={'choices': [{'message': {'content': json.dumps(content)}}]}
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        advisor.httpx,
        'AsyncClient',
        lambda **kwargs: original(transport=httpx.MockTransport(respond)),
    )
    result = await advisor.explain(evidence)
    assert result['status'] == expected
    if expected == 'available':
        assert result['strengths'] == evidence['strengths']['city_score']
        assert 'S1 и S2' in result['remaining_critical_indicators']


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
