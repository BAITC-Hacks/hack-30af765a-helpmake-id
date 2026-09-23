"""Optional narrative layer for an already calculated simulation result."""

import json
import os

from openai import AsyncOpenAI

from api.schemas.simulation import Explanation
from api.schemas.simulation import SimulationResponse


INSTRUCTIONS = (
    'Ты аналитик городских сценариев Akim AI. Ответь по-русски, кратко и ясно: '
    '4–6 предложений. Объясни, что улучшилось, какой район остаётся самым слабым, '
    'какие компромиссы связаны с бюджетом и критическими показателями. '
    'Используй только переданные расчётные данные. Не придумывай причин, прогнозов, '
    'новых показателей или фактов о реальной Астане. Не пересчитывай и не меняй числа. '
    'Данные синтетические; формулируй выводы как результат модели, а не реальный прогноз.'
)


def _advisor_input(result: SimulationResponse) -> str:
    payload = {
        'baseline_score': result.baseline_score,
        'score': result.score,
        'score_delta': result.score_delta,
        'budget': result.budget,
        'spent': result.spent,
        'remaining_budget': result.remaining_budget,
        'critical_pairs_before': result.critical_pairs_before,
        'critical_pairs_after': result.critical_pairs_after,
        'districts': [
            {
                'name': item.district_id,
                'before': item.before.district_score,
                'after': item.after.district_score,
            }
            for item in result.districts
        ],
        'measures': [
            {
                'name': item.name,
                'district': item.district_id or 'весь город',
                'cost': item.cost,
            }
            for item in result.measure_contributions
        ],
        'activated_synergies': len(result.activated_synergies),
    }
    return json.dumps(payload, ensure_ascii=False)


async def explain(result: SimulationResponse) -> Explanation:
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        return Explanation(
            status='unavailable',
            reason='AI Advisor не подключён: задайте OPENAI_API_KEY на сервере.',
        )

    client = AsyncOpenAI(api_key=api_key, timeout=12.0, max_retries=0)
    try:
        response = await client.responses.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
            instructions=INSTRUCTIONS,
            input=_advisor_input(result),
            max_output_tokens=400,
            store=False,
        )
        narrative = response.output_text.strip()
        if narrative:
            return Explanation(status='available', text=narrative)
    except Exception:
        # The deterministic simulation remains usable if the optional provider fails.
        pass
    return Explanation(
        status='unavailable',
        reason='AI Advisor временно недоступен. Числовой результат рассчитан Simulation Engine.',
    )
