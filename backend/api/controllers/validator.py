"""Pure scenario validation. Every failed rule produces a stable code."""

from collections import Counter


def validate(decisions: list[dict], dataset: dict) -> tuple[list[dict], int]:
    measures = {item['id']: item for item in dataset['measures']}
    districts = {item['code'] for item in dataset['districts']}
    violations = []
    if len(decisions) != dataset['decisions_required']:
        violations.append(
            {
                'code': 'decision_count',
                'message': f'Требуется ровно {dataset["decisions_required"]} решений.',
            }
        )
    ids = [item['measure_id'] for item in decisions]
    for measure_id, count in sorted(Counter(ids).items()):
        if count > 1:
            violations.append(
                {
                    'code': 'duplicate_measure',
                    'message': f'Мероприятие {measure_id} выбрано повторно.',
                }
            )
    directions = Counter()
    spent = 0
    for item in decisions:
        measure_id = item['measure_id']
        code = item.get('district_code')
        measure = measures.get(measure_id)
        if measure is None:
            violations.append(
                {
                    'code': 'unknown_measure',
                    'message': f'Неизвестное мероприятие: {measure_id}.',
                }
            )
            continue
        spent += measure['cost']
        directions[measure['direction']] += 1
        if measure['scope'] == 'district':
            if code is None:
                violations.append(
                    {
                        'code': 'district_required',
                        'message': f'Для {measure_id} нужно выбрать район.',
                    }
                )
            elif code not in districts:
                violations.append(
                    {'code': 'unknown_district', 'message': f'Неизвестный район: {code}.'}
                )
        elif code is not None:
            violations.append(
                {
                    'code': 'city_measure_district',
                    'message': f'Для городской меры {measure_id} район должен быть null.',
                }
            )
    if spent > dataset['budget']:
        violations.append(
            {
                'code': 'budget_exceeded',
                'message': f'Стоимость {spent} превышает бюджет {dataset["budget"]}.',
            }
        )
    for direction, count in sorted(directions.items()):
        if count > dataset['max_per_direction']:
            violations.append(
                {
                    'code': 'direction_limit',
                    'message': f'В направлении «{direction}» больше {dataset["max_per_direction"]} мер.',
                }
            )
    selected = {item['measure_id']: item.get('district_code') for item in decisions}
    for rule in dataset['incompatibilities']:
        first, second = rule['measures']
        if (
            first in selected
            and second in selected
            and (rule['scope'] == 'global' or selected[first] == selected[second])
        ):
            violations.append(
                {'code': 'incompatible_measures', 'message': rule['description']}
            )
    return violations, spent
