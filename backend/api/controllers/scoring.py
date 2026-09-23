"""Pure score calculation with full precision until API presentation."""


def calculate(indicators_by_district: dict[str, dict[str, float]], dataset: dict) -> dict:
    weights = {item['id']: item['weight'] for item in dataset['indicators']}
    district_scores = {
        code: sum(weights[key] * value for key, value in indicators.items())
        for code, indicators in indicators_by_district.items()
    }
    city_average = sum(
        item['population_share'] * district_scores[item['code']]
        for item in dataset['districts']
    )
    critical_pairs = [
        {
            'district_code': item['code'],
            'indicator': key,
            'value': indicators_by_district[item['code']][key],
        }
        for item in dataset['districts']
        for key in weights
        if indicators_by_district[item['code']][key] < dataset['critical_threshold']
    ]
    weakest = min(dataset['districts'], key=lambda item: district_scores[item['code']])['code']
    score = 0.7 * city_average + 0.3 * district_scores[weakest] - len(critical_pairs)
    return {
        'score': score,
        'city_average': city_average,
        'district_scores': district_scores,
        'critical_pairs': critical_pairs,
        'weakest_district': weakest,
    }
