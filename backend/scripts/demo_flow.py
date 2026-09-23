"""Run the complete public API flow against a running backend."""

import asyncio
import json
import os

import httpx

DECISIONS = [
    {'measure_id': 'M7', 'district_code': 'nura'},
    {'measure_id': 'M8', 'district_code': 'nura'},
    {'measure_id': 'M10', 'district_code': 'nura'},
    {'measure_id': 'M12'},
    {'measure_id': 'M5', 'district_code': 'saryarka'},
]
ALTERNATIVE = [
    *DECISIONS[:4],
    {'measure_id': 'M6'},
]


async def main() -> None:
    base_url = os.getenv('AKIM_API_URL', 'http://127.0.0.1:8000')
    saved_ids = []
    async with httpx.AsyncClient(base_url=base_url, timeout=20) as client:

        async def request(method: str, path: str, **kwargs) -> dict | list:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

        try:
            data = await request('GET', '/api/v1/data')
            result = await request('POST', '/api/v1/simulate', json={'decisions': DECISIONS})
            assert result['valid'] and result['quarters'][-1]['score'] == result['score']
            explain = await request(
                'POST',
                '/api/v1/advisor/explain',
                json={'simulation_result': result},
            )
            recommend = await request(
                'POST',
                '/api/v1/advisor/recommend',
                json={'simulation_result': result, 'goal': 'weakest_district'},
            )
            answer = await request(
                'POST',
                '/api/v1/advisor/ask',
                json={'simulation_result': result, 'question': 'Почему изменился Score?'},
            )
            first = await request(
                'POST',
                '/api/v1/scenarios',
                json={'name': 'Демо: исходный план', 'decisions': DECISIONS},
            )
            saved_ids.append(first['id'])
            second = await request(
                'POST',
                '/api/v1/scenarios',
                json={'name': 'Демо: альтернативный план', 'decisions': ALTERNATIVE},
            )
            saved_ids.append(second['id'])
            listing = await request('GET', '/api/v1/scenarios')
            loaded = await request('GET', f'/api/v1/scenarios/{first["id"]}')
            comparison = await request(
                'POST',
                '/api/v1/scenarios/compare',
                json={'left_id': first['id'], 'right_id': second['id']},
            )
            assert loaded['result'] == result
            print(
                json.dumps(
                    {
                        'dataset_version': data['version'],
                        'budget': data['budget'],
                        'score_q0': result['quarters'][0]['score'],
                        'score_q8': result['quarters'][8]['score'],
                        'advisor_statuses': {
                            'explain': explain['status'],
                            'recommend': recommend['status'],
                            'ask': answer['status'],
                        },
                        'saved_scenarios_visible': len(listing),
                        'comparison_score_delta': comparison['score_delta'],
                        'comparison_spent_delta': comparison['spent_delta'],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        finally:
            for scenario_id in saved_ids:
                response = await client.delete(f'/api/v1/scenarios/{scenario_id}')
                response.raise_for_status()


if __name__ == '__main__':
    asyncio.run(main())
