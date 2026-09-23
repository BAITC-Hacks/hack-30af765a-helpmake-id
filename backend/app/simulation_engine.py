"""Deterministic Akim AI simulation using the shared GitHub dataset."""

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

from api.schemas.simulation import DecisionInput
from api.schemas.simulation import DistrictSnapshot
from api.schemas.simulation import DistrictComparison
from api.schemas.simulation import Explanation
from api.schemas.simulation import IndicatorEffect
from api.schemas.simulation import MeasureContribution
from api.schemas.simulation import SimulationDataResponse
from api.schemas.simulation import SimulationRequest
from api.schemas.simulation import SimulationResponse
from api.schemas.simulation import SynergyApplied


DATA_PATH = Path(__file__).resolve().parents[1] / 'data' / 'simulation.json'


class ScenarioError(ValueError):
    """A user scenario violates a rule defined by the simulation dataset."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@lru_cache(maxsize=1)
def get_data() -> SimulationDataResponse:
    raw = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    weights = {item['id']: item['weight'] for item in raw['indicators']}
    baseline = _snapshots(raw['districts'], weights)
    score, _, _, _ = _score(baseline)
    return SimulationDataResponse.model_validate({**raw, 'baseline_score': score})


def _snapshots(districts: list, weights: dict[str, float]) -> list[DistrictSnapshot]:
    return [
        DistrictSnapshot(
            district_id=district['id'],
            population_share=district['population_share'],
            indicators={key: round(float(value), 3) for key, value in district['indicators'].items()},
            district_score=round(
                sum(weights[key] * value for key, value in district['indicators'].items()),
                2,
            ),
        )
        for district in districts
    ]


def _score(snapshots: list[DistrictSnapshot]) -> tuple[float, float, float, int]:
    city = sum(district.population_share * district.district_score for district in snapshots)
    weakest = min(district.district_score for district in snapshots)
    critical = sum(value < 40 for district in snapshots for value in district.indicators.values())
    return round(0.7 * city + 0.3 * weakest - critical, 2), round(city, 2), weakest, critical


def _validate(request: SimulationRequest, data: SimulationDataResponse) -> tuple[list, int]:
    measures = {measure.id: measure for measure in data.measures}
    districts = {district.id for district in data.districts}
    ids = [decision.measure_id for decision in request.decisions]
    if len(set(ids)) != len(ids):
        raise ScenarioError('duplicate_measure', 'Одну инициативу нельзя выбирать повторно.')

    selected = []
    for decision in request.decisions:
        measure = measures.get(decision.measure_id)
        if measure is None:
            raise ScenarioError('unknown_measure', f'Неизвестная инициатива: {decision.measure_id}.')
        if measure.type == 'Район' and decision.district_id not in districts:
            raise ScenarioError('district_required', f'Для «{measure.name}» укажите район.')
        if measure.type == 'Город' and decision.district_id is not None:
            raise ScenarioError('city_scope', f'Для «{measure.name}» район указывать нельзя.')
        selected.append(measure)

    spent = sum(measure.cost for measure in selected)
    if spent > data.budget:
        raise ScenarioError('over_budget', f'Бюджет превышен на {spent - data.budget} ед.')

    directions = Counter(measure.direction for measure in selected)
    if any(count > 2 for count in directions.values()):
        raise ScenarioError('direction_limit', 'В одном направлении можно выбрать не более двух мер.')

    by_id = {decision.measure_id: decision for decision in request.decisions}
    for rule in data.incompatibilities:
        if not all(measure_id in by_id for measure_id in rule.measures):
            continue
        if rule.scope == 'global':
            raise ScenarioError('incompatible', rule.description)
        targets = {by_id[measure_id].district_id for measure_id in rule.measures}
        if len(targets) == 1:
            raise ScenarioError('incompatible', rule.description)
    return selected, spent


def simulate(request: SimulationRequest) -> SimulationResponse:
    data = get_data()
    selected, spent = _validate(request, data)
    weights = {indicator.id: indicator.weight for indicator in data.indicators}
    before = _snapshots([district.model_dump() for district in data.districts], weights)
    values = {
        district.id: {key: float(value) for key, value in district.indicators.items()}
        for district in data.districts
    }
    contributions = []

    for decision, measure in zip(request.decisions, selected, strict=True):
        affected = [decision.district_id] if measure.type == 'Район' else list(values)
        factor = (data.horizon_quarters - measure.lag) / data.horizon_quarters
        effects = []
        for indicator, full_effect in measure.effects.items():
            applied = full_effect * factor
            for district_id in affected:
                values[district_id][indicator] += applied
            effects.append(
                IndicatorEffect(
                    indicator=indicator,
                    full_effect=full_effect,
                    applied_effect=round(applied, 3),
                ),
            )
        contributions.append(
            MeasureContribution(
                measure_id=measure.id,
                name=measure.name,
                direction=measure.direction,
                type=measure.type,
                district_id=decision.district_id,
                affected_districts=affected,
                cost=measure.cost,
                lag=measure.lag,
                effect_factor=round(factor, 3),
                indicator_effects=effects,
            ),
        )

    by_id: dict[str, DecisionInput] = {
        decision.measure_id: decision for decision in request.decisions
    }
    synergies = []
    for rule in data.synergies:
        if not all(measure_id in by_id for measure_id in rule.measures):
            continue
        source = by_id[rule.district_from]
        affected = [source.district_id] if source.district_id else list(values)
        for district_id in affected:
            values[district_id][rule.indicator] += rule.bonus
            synergies.append(
                SynergyApplied(
                    measures=rule.measures,
                    indicator=rule.indicator,
                    bonus=rule.bonus,
                    district_id=district_id,
                ),
            )

    for indicators in values.values():
        for indicator, value in indicators.items():
            indicators[indicator] = min(100.0, max(0.0, value))
    after_data = [
        {
            'id': district.id,
            'population_share': district.population_share,
            'indicators': values[district.id],
        }
        for district in data.districts
    ]
    after = _snapshots(after_data, weights)
    baseline_score, city_before, weakest_before, critical_before = _score(before)
    score, city_after, weakest_after, critical_after = _score(after)

    return SimulationResponse(
        decisions=request.decisions,
        budget=data.budget,
        spent=spent,
        remaining_budget=data.budget - spent,
        score=score,
        baseline_score=baseline_score,
        score_delta=round(score - baseline_score, 2),
        city_score_before=city_before,
        city_score_after=city_after,
        weakest_district_score_before=weakest_before,
        weakest_district_score_after=weakest_after,
        critical_pairs_before=critical_before,
        critical_pairs_after=critical_after,
        districts=[
            DistrictComparison(district_id=old.district_id, before=old, after=new)
            for old, new in zip(before, after, strict=True)
        ],
        measure_contributions=contributions,
        activated_synergies=synergies,
        ai_explanation=Explanation(
            status='unavailable',
            reason='AI Advisor не подключён. Числовые результаты рассчитаны Simulation Engine.',
        ),
    )
