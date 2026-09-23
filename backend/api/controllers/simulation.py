"""Orchestrate validation, pure simulation, and scoring."""

from . import dataset as dataset_controller
from . import scoring, validator


def _round(value: float) -> float:
    return round(value, 2)


def _snapshot(dataset: dict) -> dict[str, dict[str, float]]:
    return {
        district['code']: dict(district['indicators']) for district in dataset['districts']
    }


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
    after = _snapshot(dataset)
    measures = {item['id']: item for item in dataset['measures']}
    district_codes = [item['code'] for item in dataset['districts']]
    contributions = []
    selected = {item['measure_id']: item.get('district_code') for item in decisions}
    for decision in result['decisions']:
        measure = measures[decision['measure_id']]
        targets = district_codes if measure['scope'] == 'city' else [decision['district_code']]
        factor = (dataset['horizon_quarters'] - measure['lag']) / dataset['horizon_quarters']
        effects = {key: value * factor for key, value in measure['effects'].items()}
        for code in targets:
            for indicator, effect in effects.items():
                after[code][indicator] += effect
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
            after[code][synergy['indicator']] += synergy['bonus']
            activated.append(
                {
                    'measures': synergy['measures'],
                    'district_code': code,
                    'indicator': synergy['indicator'],
                    'bonus': synergy['bonus'],
                }
            )
    for indicators in after.values():
        for key, value in indicators.items():
            indicators[key] = min(100, max(0, value))

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
        }
    )
    return result
