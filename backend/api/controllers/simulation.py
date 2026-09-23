"""Orchestrate validation, pure simulation, and scoring."""

from . import dataset as dataset_controller
from . import scoring, validator


def _round(value: float) -> float:
    return round(value, 2)


def _snapshot(dataset: dict) -> dict[str, dict[str, float]]:
    return {
        district['code']: dict(district['indicators']) for district in dataset['districts']
    }


def _effect_factor(quarter: int, lag: int, horizon: int) -> float:
    return max(0, quarter - lag) / horizon


def _state_at_quarter(
    quarter: int,
    dataset: dict,
    decisions: list[dict],
) -> dict[str, dict[str, float]]:
    state = _snapshot(dataset)
    measures = {item['id']: item for item in dataset['measures']}
    district_codes = [item['code'] for item in dataset['districts']]
    selected = {item['measure_id']: item.get('district_code') for item in decisions}
    for decision in decisions:
        measure = measures[decision['measure_id']]
        targets = district_codes if measure['scope'] == 'city' else [decision['district_code']]
        factor = _effect_factor(quarter, measure['lag'], dataset['horizon_quarters'])
        for code in targets:
            for indicator, effect in measure['effects'].items():
                state[code][indicator] += effect * factor
    for synergy in dataset['synergies']:
        if all(measure_id in selected for measure_id in synergy['measures']) and quarter > max(
            measures[measure_id]['lag'] for measure_id in synergy['measures']
        ):
            code = selected[synergy['district_from']]
            state[code][synergy['indicator']] += synergy['bonus']
    for indicators in state.values():
        for key, value in indicators.items():
            indicators[key] = min(100, max(0, value))
    return state


def simulate(decisions: list[dict]) -> dict:
    dataset = dataset_controller.load_dataset()
    violations, spent = validator.validate(decisions, dataset)
    result = {
        'valid': not violations,
        'dataset_version': dataset['version'],
        'dataset_hash': dataset['dataset_hash'],
        'budget': dataset['budget'],
        'spent': spent,
        'remaining_budget': dataset['budget'] - spent,
        'violations': violations,
        'decisions': sorted(decisions, key=lambda item: item['measure_id']),
    }
    if violations:
        return result

    before = _snapshot(dataset)
    measures = {item['id']: item for item in dataset['measures']}
    district_codes = [item['code'] for item in dataset['districts']]
    contributions = []
    selected = {item['measure_id']: item.get('district_code') for item in decisions}
    for decision in result['decisions']:
        measure = measures[decision['measure_id']]
        targets = district_codes if measure['scope'] == 'city' else [decision['district_code']]
        factor = _effect_factor(
            dataset['horizon_quarters'], measure['lag'], dataset['horizon_quarters']
        )
        effects = {key: value * factor for key, value in measure['effects'].items()}
        contributions.append(
            {
                'measure_id': measure['id'],
                'district_code': decision.get('district_code'),
                'affected_districts': targets,
                'cost': measure['cost'],
                'lag': measure['lag'],
                'effect_factor': factor,
                'full_effects': measure['effects'],
                'applied_effects': effects,
            }
        )
    activated = []
    for synergy in dataset['synergies']:
        if all(measure_id in selected for measure_id in synergy['measures']):
            code = selected[synergy['district_from']]
            activated.append(
                {
                    'measures': synergy['measures'],
                    'district_code': code,
                    'indicator': synergy['indicator'],
                    'bonus': synergy['bonus'],
                }
            )
    quarters = []
    for quarter in range(dataset['horizon_quarters'] + 1):
        state = _state_at_quarter(quarter, dataset, result['decisions'])
        scores = scoring.calculate(state, dataset)
        quarters.append(
            {
                'quarter': quarter,
                'score': _round(scores['score']),
                'city_average': _round(scores['city_average']),
                'weakest_district': scores['weakest_district'],
                'critical_pairs': scores['critical_pairs'],
                'districts': [
                    {
                        'district_code': district['code'],
                        'score': _round(scores['district_scores'][district['code']]),
                        'indicators': state[district['code']],
                    }
                    for district in dataset['districts']
                ],
            }
        )
    after = {item['district_code']: item['indicators'] for item in quarters[-1]['districts']}
    baseline = scoring.calculate(before, dataset)
    final = scoring.calculate(after, dataset)
    result.update(
        {
            'baseline_score': _round(baseline['score']),
            'score': _round(final['score']),
            'score_delta': _round(final['score'] - baseline['score']),
            'city_average_before': _round(baseline['city_average']),
            'city_average_after': _round(final['city_average']),
            'critical_pairs_before': baseline['critical_pairs'],
            'critical_pairs_after': final['critical_pairs'],
            'weakest_district_before': baseline['weakest_district'],
            'weakest_district_after': final['weakest_district'],
            'districts': [
                {
                    'code': district['code'],
                    'name': district['name'],
                    'population_share': district['population_share'],
                    'before': {
                        'indicators': before[district['code']],
                        'score': _round(baseline['district_scores'][district['code']]),
                    },
                    'after': {
                        'indicators': after[district['code']],
                        'score': _round(final['district_scores'][district['code']]),
                    },
                }
                for district in dataset['districts']
            ],
            'measure_contributions': contributions,
            'activated_synergies': activated,
            'quarters': quarters,
        }
    )
    return result
