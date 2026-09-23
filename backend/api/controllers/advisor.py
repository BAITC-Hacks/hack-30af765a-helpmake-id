"""Validate advisor input against the authoritative simulation."""

import fastapi

from ..webhooks import advisor as advisor_adapter
from . import dataset, simulation, validator


def _verified_result(submitted: dict) -> dict | None:
    if not submitted['valid']:
        return None
    current = simulation.simulate(submitted['decisions'])
    if not current['valid'] or any(
        submitted.get(field) != current.get(field) for field in current if field != 'quarters'
    ):
        return None
    if submitted.get('quarters') and submitted['quarters'] != current['quarters']:
        return None
    return current


async def explain(submitted: dict) -> dict:
    current = _verified_result(submitted)
    if current is None:
        return {'status': 'unavailable', 'reason': 'Simulation result is stale or altered.'}
    return await advisor_adapter.explain(
        _explanation_evidence(current, dataset.load_dataset())
    )


def _explanation_evidence(result: dict, source: dict) -> dict[str, dict[str, str]]:
    """Offer the model only server-written statements backed by this result."""
    district_names = {item['code']: item['name'] for item in result['districts']}
    indicator_names = {item['id']: item['name'] for item in source['indicators']}
    measure_names = {item['id']: item['name'] for item in source['measures']}
    best = max(
        result['districts'],
        key=lambda item: item['after']['score'] - item['before']['score'],
    )
    best_delta = round(best['after']['score'] - best['before']['score'], 2)
    weakest_code = result['weakest_district_after']
    weakest = next(item for item in result['districts'] if item['code'] == weakest_code)
    critical = result['critical_pairs_after']
    critical_text = (
        'После сценария критическими остаются: '
        + ', '.join(
            f'{district_names[item["district_code"]]} — '
            f'{indicator_names[item["indicator"]]} ({item["indicator"]}: {item["value"]:g})'
            for item in critical
        )
        + '.'
        if critical
        else 'После сценария критических показателей нет.'
    )
    evidence = {
        'strengths': {
            'city_score': (
                f'Городской Score изменился с {result["baseline_score"]:.2f} '
                f'до {result["score"]:.2f} ({result["score_delta"]:+.2f}).'
            ),
            'best_district': (
                f'Наибольшее изменение районного Score у района {best["name"]}: '
                f'{best["before"]["score"]:.2f} → {best["after"]["score"]:.2f} '
                f'({best_delta:+.2f}).'
            ),
        },
        'weaknesses': {
            'weakest_district': (
                f'Слабейшим после сценария остаётся район {weakest["name"]} '
                f'со Score {weakest["after"]["score"]:.2f}.'
            ),
            'critical_count': (
                f'После сценария критических пар район–показатель: {len(critical)}.'
            ),
        },
        'tradeoffs': {
            'budget': (
                f'Из бюджета {result["budget"]} потрачено {result["spent"]}; '
                f'осталось {result["remaining_budget"]}.'
            ),
            'critical_change': (
                'Число критических пар изменилось с '
                f'{len(result["critical_pairs_before"])} до {len(critical)} '
                f'при изменении городского Score на {result["score_delta"]:+.2f}.'
            ),
        },
        'remaining_critical_indicators': {'critical_pairs': critical_text},
    }
    if not critical:
        del evidence['weaknesses']['critical_count']
    negative = [
        (contribution, indicator, value)
        for contribution in result['measure_contributions']
        for indicator, value in contribution['applied_effects'].items()
        if value < 0
    ]
    if negative:
        contribution, indicator, value = negative[0]
        evidence['tradeoffs']['negative_effect'] = (
            f'Мера {contribution["measure_id"]} '
            f'«{measure_names[contribution["measure_id"]]}» уменьшает показатель '
            f'«{indicator_names[indicator]}» на {abs(value):g} '
            'в затронутом районе до учёта остальных мер.'
        )
    return evidence


def _goal_value(result: dict, goal: str, source: dict, target: str | None) -> float:
    if goal == 'balanced':
        return result['score']
    if goal == 'weakest_district':
        code = target or result['weakest_district_after']
        return next(
            item['after']['score'] for item in result['districts'] if item['code'] == code
        )
    direction = 'Транспорт' if goal == 'transport' else 'Экология'
    weights = {
        item['id']: item['weight']
        for item in source['indicators']
        if item['direction'] == direction
    }
    districts = (
        [item for item in result['districts'] if item['code'] == target]
        if target is not None
        else result['districts']
    )
    return sum(
        (1 if target is not None else district['population_share'])
        * sum(weights[key] * district['after']['indicators'][key] for key in weights)
        for district in districts
    )


def _recommendation_candidates(
    current: dict,
    goal: str,
    constraints: dict,
    source: dict,
) -> list[dict]:
    measures = {item['id']: item for item in source['measures']}
    selected = {item['measure_id'] for item in current['decisions']}
    locked = set(constraints['locked_measure_ids'])
    excluded = set(constraints['excluded_measure_ids'])
    unknown = (locked | excluded) - measures.keys()
    if unknown:
        raise fastapi.HTTPException(422, detail=f'Unknown measure IDs: {sorted(unknown)}')
    if locked - selected:
        raise fastapi.HTTPException(
            422, detail='Locked measures must be in the current scenario.'
        )
    if locked & excluded:
        raise fastapi.HTTPException(
            422, detail='A measure cannot be both locked and excluded.'
        )
    target = constraints['target_district_code']
    if target is not None and target not in {item['code'] for item in source['districts']}:
        raise fastapi.HTTPException(422, detail='Unknown target district_code.')
    focus_district = target or current['weakest_district_after']
    current_value = _goal_value(
        current,
        goal,
        source,
        focus_district if goal == 'weakest_district' else target,
    )
    candidates = []
    for replaced in current['decisions']:
        if replaced['measure_id'] in locked:
            continue
        for measure in source['measures']:
            if measure['id'] in selected or measure['id'] in excluded:
                continue
            targets = (
                [None]
                if measure['scope'] == 'city'
                else [district['code'] for district in source['districts']]
            )
            for district_code in targets:
                replacement = {'measure_id': measure['id'], 'district_code': district_code}
                decisions = [
                    replacement if item['measure_id'] == replaced['measure_id'] else item
                    for item in current['decisions']
                ]
                if any(item['measure_id'] in excluded for item in decisions):
                    continue
                violations, spent = validator.validate(decisions, source)
                if violations or (
                    constraints['max_spent'] is not None and spent > constraints['max_spent']
                ):
                    continue
                result = simulation.simulate(decisions)
                if not result['valid']:
                    continue
                goal_gain = (
                    _goal_value(
                        result,
                        goal,
                        source,
                        focus_district if goal == 'weakest_district' else target,
                    )
                    - current_value
                )
                if goal_gain <= 0:
                    continue
                score_delta = round(result['score'] - current['score'], 2)
                spent_delta = result['spent'] - current['spent']
                critical_delta = len(result['critical_pairs_after']) - len(
                    current['critical_pairs_after']
                )
                district_name = next(
                    (
                        district['name']
                        for district in source['districts']
                        if district['code'] == district_code
                    ),
                    'весь город',
                )
                tradeoff = (
                    f'Замена «{measures[replaced["measure_id"]]["name"]}» на '
                    f'«{measure["name"]}» ({district_name}) улучшает выбранную цель. '
                    f'Score изменится на {score_delta:+.2f}, расходы на {spent_delta:+d}, '
                    f'число критических показателей на {critical_delta:+d}.'
                )
                candidates.append(
                    {
                        'replaces': replaced,
                        'with_decision': replacement,
                        'decisions': result['decisions'],
                        'spent': result['spent'],
                        'score': result['score'],
                        'score_delta': score_delta,
                        'tradeoff': tradeoff,
                        'goal_gain': round(goal_gain, 4),
                    }
                )
    candidates.sort(
        key=lambda item: (
            -item['goal_gain'],
            -item['score_delta'],
            item['replaces']['measure_id'],
            item['with_decision']['measure_id'],
            item['with_decision']['district_code'] or '',
        )
    )
    return candidates[:12]


async def recommend(submitted: dict, goal: str, constraints: dict) -> dict:
    current = _verified_result(submitted)
    if current is None:
        return {'status': 'unavailable', 'reason': 'Simulation result is stale or altered.'}
    source = dataset.load_dataset()
    candidates = _recommendation_candidates(current, goal, constraints, source)
    response = await advisor_adapter.recommend(current, goal, constraints, candidates, source)
    if response['status'] != 'available':
        return response
    verified = []
    for item in response['recommendations']:
        violations, spent = validator.validate(item['decisions'], source)
        if violations or (
            constraints['max_spent'] is not None and spent > constraints['max_spent']
        ):
            continue
        calculated = simulation.simulate(item['decisions'])
        if not calculated['valid'] or calculated['dataset_hash'] != current['dataset_hash']:
            continue
        verified.append(
            {
                **item,
                'decisions': calculated['decisions'],
                'spent': calculated['spent'],
                'score': calculated['score'],
                'score_delta': round(calculated['score'] - current['score'], 2),
            }
        )
    return {'status': 'available', 'recommendations': verified}


async def ask(submitted: dict, question: str) -> dict:
    current = _verified_result(submitted)
    if current is None:
        return {'status': 'unavailable', 'reason': 'Simulation result is stale or altered.'}
    facts = _ask_facts(current, dataset.load_dataset())
    response = await advisor_adapter.ask(question, facts)
    if response['status'] != 'available':
        return response
    return {
        'status': 'available',
        'answer': ' '.join(facts[fact_id] for fact_id in response['fact_ids']),
    }


def _ask_facts(result: dict, source: dict) -> dict[str, str]:
    indicators = {item['id']: item['name'] for item in source['indicators']}
    facts = {
        'score': (
            f'Итоговый Score равен {result["score"]}; изменение к исходному состоянию '
            f'составляет {result["score_delta"]:+.2f}.'
        ),
        'formula': (
            'Score рассчитывается из среднего районного балла с учётом населения, '
            'балла слабейшего района и штрафа за критические показатели.'
        ),
        'budget': (
            f'Из бюджета {result["budget"]} потрачено {result["spent"]}, '
            f'осталось {result["remaining_budget"]}.'
        ),
        'weakest': (
            f'Слабейший район до сценария: {result["weakest_district_before"]}; '
            f'после сценария: {result["weakest_district_after"]}.'
        ),
        'critical': (
            'После сценария критические показатели: '
            + (
                ', '.join(
                    f'{item["district_code"]} — {indicators[item["indicator"]]} '
                    f'({item["value"]})'
                    for item in result['critical_pairs_after']
                )
                or 'отсутствуют'
            )
            + '.'
        ),
    }
    for district in result['districts']:
        changes = [
            f'{indicators[key]}: {before} → {district["after"]["indicators"][key]}'
            for key, before in district['before']['indicators'].items()
            if before != district['after']['indicators'][key]
        ]
        facts[f'district_{district["code"]}'] = (
            f'Район {district["name"]}: районный Score изменился с '
            f'{district["before"]["score"]} до {district["after"]["score"]}; '
            f'изменения показателей: {", ".join(changes) if changes else "нет"}.'
        )
    for measure in source['measures']:
        effects = ', '.join(
            f'{indicators[key]} {effect:+d}' for key, effect in measure['effects'].items()
        )
        facts[f'measure_{measure["id"]}'] = (
            f'Мера {measure["id"]} «{measure["name"]}»: стоимость {measure["cost"]}, '
            f'полный эффект до учёта лага: {effects}.'
        )
    return facts
