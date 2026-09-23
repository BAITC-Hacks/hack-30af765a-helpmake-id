"""Optional OpenAI-compatible chat-completion adapter for qualitative explanations."""

import json
import os
import re

import httpx

FIELDS = ('strengths', 'weaknesses', 'tradeoffs', 'remaining_critical_indicators')
NUMBER_WORDS = re.compile(
    r'\b(?:ноль|один|одна|одно|два|две|три|четыре|пять|шесть|семь|восемь|'
    r'девять|десять|сто|тысяча|тысячи|тысяч|one|two|three|four|five|six|'
    r'seven|eight|nine|ten|hundred|thousand)\b',
    re.IGNORECASE,
)


async def explain(result: dict) -> dict:
    url = os.getenv('AI_API_URL')
    key = os.getenv('AI_API_KEY')
    model = os.getenv('AI_MODEL')
    if not all((url, key, model)):
        return {'status': 'unavailable', 'reason': 'AI provider is not configured.'}

    facts = {
        'score_delta': result['score_delta'],
        'weakest_district': result['weakest_district_after'],
        'critical_pairs_after': result['critical_pairs_after'],
        'districts': result['districts'],
        'measure_contributions': result['measure_contributions'],
        'activated_synergies': result['activated_synergies'],
    }
    prompt = (
        'Объясни результаты симуляции на русском языке. Верни только JSON с ключами '
        'strengths, weaknesses, tradeoffs, remaining_critical_indicators. '
        'Для каждого ключа дай краткий текст. Не добавляй никаких чисел, цифр, '
        'новых фактов или рекомендаций. Используй только предоставленный результат.'
    )
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                url,
                headers={'Authorization': f'Bearer {key}'},
                json={
                    'model': model,
                    'temperature': 0,
                    'messages': [
                        {'role': 'system', 'content': prompt},
                        {'role': 'user', 'content': json.dumps(facts, ensure_ascii=False)},
                    ],
                },
            )
            response.raise_for_status()
        payload = json.loads(response.json()['choices'][0]['message']['content'])
        if set(payload) != set(FIELDS) or any(
            not isinstance(payload[field], str)
            or not payload[field].strip()
            or len(payload[field]) > 1200
            or re.search(r'\d', payload[field])
            or NUMBER_WORDS.search(payload[field])
            for field in FIELDS
        ):
            raise ValueError('Invalid advisor response')
        return {'status': 'available', **payload}
    except (
        httpx.HTTPError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return {
            'status': 'unavailable',
            'reason': 'AI provider could not produce a valid explanation.',
        }
