"""Check the published numbers and the scenario rules at their pure boundaries."""

import copy

import pytest

from api.controllers import dataset, scoring, simulation, validator


def decision(measure_id, district_code=None):
    return {'measure_id': measure_id, 'district_code': district_code}


EXAMPLE = [
    decision('M7', 'nura'),
    decision('M8', 'nura'),
    decision('M10', 'nura'),
    decision('M12'),
    decision('M5', 'saryarka'),
]


def codes(decisions):
    violations, _ = validator.validate(decisions, dataset.load_dataset())
    return {item['code'] for item in violations}


def test_dataset_and_baseline():
    source = dataset.load_dataset()
    assert sum(item['population_share'] for item in source['districts']) == pytest.approx(1)
    assert sum(item['weight'] for item in source['indicators']) == pytest.approx(1)
    baseline = scoring.calculate(
        {item['code']: item['indicators'] for item in source['districts']},
        source,
    )
    assert baseline['score'] == pytest.approx(52.55768)
    assert {
        (pair['district_code'], pair['indicator']) for pair in baseline['critical_pairs']
    } == {
        ('nura', 'S1'),
        ('nura', 'S2'),
    }
    clone = dataset.public_data()
    clone['budget'] = 0
    assert dataset.load_dataset()['budget'] == 100


def test_example_and_order_independence():
    result = simulation.simulate(EXAMPLE)
    assert result['valid'] is True
    assert result['spent'] == 95
    assert result['baseline_score'] == 52.56
    assert result['score'] == 56.54
    assert result['score_delta'] == 3.99
    assert result['activated_synergies'] == [
        {'measures': ['M10', 'M12'], 'district_code': 'nura', 'indicator': 'B1', 'bonus': 2}
    ]
    assert result == simulation.simulate(list(reversed(EXAMPLE)))
    assert result == simulation.simulate(EXAMPLE)


def test_quarters_reuse_the_final_simulation_and_respect_lags():
    result = simulation.simulate(EXAMPLE)
    quarters = result['quarters']
    assert [item['quarter'] for item in quarters] == list(range(9))
    assert quarters[0]['score'] == result['baseline_score']
    assert quarters[8]['score'] == result['score']
    assert quarters[8]['city_average'] == result['city_average_after']
    assert quarters[8]['critical_pairs'] == result['critical_pairs_after']
    for district in result['districts']:
        code = district['code']
        initial = next(
            item for item in quarters[0]['districts'] if item['district_code'] == code
        )
        final = next(
            item for item in quarters[8]['districts'] if item['district_code'] == code
        )
        assert initial == {'district_code': code, **district['before']}
        assert final == {'district_code': code, **district['after']}
    nura_q3 = next(
        item for item in quarters[3]['districts'] if item['district_code'] == 'nura'
    )
    assert nura_q3['indicators']['S1'] == 38
    nura_q4 = next(
        item for item in quarters[4]['districts'] if item['district_code'] == 'nura'
    )
    assert nura_q4['indicators']['S1'] > 38
    assert quarters == simulation.simulate(list(reversed(EXAMPLE)))['quarters']


@pytest.mark.parametrize(
    ('decisions', 'expected'),
    [
        (EXAMPLE[:4], 'decision_count'),
        (EXAMPLE + [decision('M9', 'nura')], 'decision_count'),
        ([EXAMPLE[0], EXAMPLE[0], *EXAMPLE[2:]], 'duplicate_measure'),
        ([decision('M99', 'nura'), *EXAMPLE[1:]], 'unknown_measure'),
        ([decision('M7'), *EXAMPLE[1:]], 'district_required'),
        ([decision('M7', 'unknown'), *EXAMPLE[1:]], 'unknown_district'),
        ([*EXAMPLE[:3], decision('M12', 'nura'), EXAMPLE[4]], 'city_measure_district'),
        (
            [
                decision('M3', 'nura'),
                decision('M5', 'nura'),
                decision('M7', 'nura'),
                decision('M8', 'nura'),
                decision('M13', 'esil'),
            ],
            'budget_exceeded',
        ),
        (
            [
                decision('M7', 'nura'),
                decision('M8', 'nura'),
                decision('M9', 'nura'),
                decision('M10', 'nura'),
                decision('M12'),
            ],
            'direction_limit',
        ),
        (
            [
                decision('M1', 'nura'),
                decision('M3', 'esil'),
                decision('M9', 'nura'),
                decision('M10', 'nura'),
                decision('M12'),
            ],
            'incompatible_measures',
        ),
        (
            [
                decision('M4', 'nura'),
                decision('M7', 'nura'),
                decision('M9', 'nura'),
                decision('M10', 'nura'),
                decision('M12'),
            ],
            'incompatible_measures',
        ),
        (
            [
                decision('M5', 'nura'),
                decision('M13', 'nura'),
                decision('M9', 'nura'),
                decision('M10', 'nura'),
                decision('M12'),
            ],
            'incompatible_measures',
        ),
    ],
)
def test_validation_codes(decisions, expected):
    assert expected in codes(decisions)
    result = simulation.simulate(decisions)
    assert result['valid'] is False
    assert 'score' not in result


def test_same_district_conflicts_allow_different_districts():
    assert 'incompatible_measures' not in codes(
        [
            decision('M4', 'nura'),
            decision('M7', 'esil'),
            decision('M9', 'nura'),
            decision('M10', 'nura'),
            decision('M12'),
        ]
    )


def test_negative_effect_and_synergies():
    result = simulation.simulate(
        [
            decision('M1', 'nura'),
            decision('M2'),
            decision('M5', 'saryarka'),
            decision('M6'),
            decision('M11', 'nura'),
        ]
    )
    assert result['valid']
    assert len(result['activated_synergies']) == 2
    nura = next(item for item in result['districts'] if item['code'] == 'nura')
    assert nura['after']['indicators']['T1'] == pytest.approx(
        55 + 6 * 0.75 + 4 * 0.75 + 2 - 2 * 0.875
    )
    q2_nura = next(
        item for item in result['quarters'][2]['districts'] if item['district_code'] == 'nura'
    )
    q3_nura = next(
        item for item in result['quarters'][3]['districts'] if item['district_code'] == 'nura'
    )
    assert q3_nura['indicators']['T1'] - q2_nura['indicators']['T1'] == pytest.approx(3)


def test_clipping_and_strict_critical_threshold(monkeypatch):
    source = copy.deepcopy(dataset.load_dataset())
    source['districts'][0]['indicators']['T1'] = 99
    source['districts'][0]['indicators']['B2'] = 0
    monkeypatch.setattr(dataset, 'load_dataset', lambda: source)
    result = simulation.simulate(
        [
            decision('M2'),
            decision('M4', 'esil'),
            decision('M8', 'nura'),
            decision('M10', 'esil'),
            decision('M11', 'esil'),
        ]
    )
    assert result['valid']
    esil = next(item for item in result['districts'] if item['code'] == 'esil')
    assert esil['after']['indicators']['T1'] == 100
    assert esil['after']['indicators']['B2'] >= 0
    state = {item['code']: dict(item['indicators']) for item in source['districts']}
    state['nura']['S1'] = 40
    state['nura']['S2'] = 39.999
    critical = scoring.calculate(state, source)['critical_pairs']
    assert ('nura', 'S1') not in {
        (pair['district_code'], pair['indicator']) for pair in critical
    }
    assert ('nura', 'S2') in {(pair['district_code'], pair['indicator']) for pair in critical}
