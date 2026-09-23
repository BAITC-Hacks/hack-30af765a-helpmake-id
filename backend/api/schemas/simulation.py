import typing

import pydantic


class DecisionInput(pydantic.BaseModel):
    measure_id: typing.Annotated[
        str,
        pydantic.StringConstraints(
            strict=True,
            min_length=2,
            max_length=8,
        ),
    ]
    district_id: typing.Annotated[
        str,
        pydantic.StringConstraints(
            strict=True,
            min_length=1,
            max_length=32,
        ),
    ] | None = None

    model_config = pydantic.ConfigDict(extra='forbid')


class SimulationRequest(pydantic.BaseModel):
    decisions: list[DecisionInput]

    model_config = pydantic.ConfigDict(extra='forbid')

    @pydantic.field_validator('decisions')
    @classmethod
    def require_five_decisions(cls, value: list[DecisionInput]) -> list[DecisionInput]:
        if len(value) != 5:
            raise ValueError('Ровно 5 решений обязательны.')
        return value


class IndicatorData(pydantic.BaseModel):
    id: str
    direction: str
    name: str
    description: str
    weight: float


class DistrictData(pydantic.BaseModel):
    id: str
    population_share: float
    profile: str
    indicators: dict[str, int]
    expected_score: float


class MeasureData(pydantic.BaseModel):
    id: str
    direction: str
    name: str
    type: typing.Literal['Район', 'Город']
    cost: int
    lag: int
    effects: dict[str, int]


class SynergyData(pydantic.BaseModel):
    measures: list[str]
    indicator: str
    bonus: int
    district_from: str


class IncompatibilityData(pydantic.BaseModel):
    measures: list[str]
    scope: typing.Literal['global', 'same_district']
    description: str


class SimulationDataResponse(pydantic.BaseModel):
    budget: int
    horizon_quarters: int
    directions: list[str]
    indicators: list[IndicatorData]
    districts: list[DistrictData]
    measures: list[MeasureData]
    synergies: list[SynergyData]
    incompatibilities: list[IncompatibilityData]


class IndicatorEffect(pydantic.BaseModel):
    indicator: str
    full_effect: float
    applied_effect: float


class MeasureContribution(pydantic.BaseModel):
    measure_id: str
    name: str
    direction: str
    type: typing.Literal['Район', 'Город']
    district_id: str | None
    affected_districts: list[str]
    cost: int
    lag: int
    effect_factor: float
    indicator_effects: list[IndicatorEffect]


class SynergyApplied(pydantic.BaseModel):
    measures: list[str]
    indicator: str
    bonus: float
    district_id: str


class DistrictSnapshot(pydantic.BaseModel):
    district_id: str
    population_share: float
    indicators: dict[str, float]
    district_score: float


class DistrictComparison(pydantic.BaseModel):
    district_id: str
    before: DistrictSnapshot
    after: DistrictSnapshot


class Explanation(pydantic.BaseModel):
    status: typing.Literal['available', 'unavailable']
    text: str | None = None
    reason: str | None = None


class SimulationResponse(pydantic.BaseModel):
    decisions: list[DecisionInput]
    budget: int
    spent: int
    remaining_budget: int
    score: float
    baseline_score: float
    score_delta: float
    city_score_before: float
    city_score_after: float
    weakest_district_score_before: float
    weakest_district_score_after: float
    critical_pairs_before: int
    critical_pairs_after: int
    districts: list[DistrictComparison]
    measure_contributions: list[MeasureContribution]
    activated_synergies: list[SynergyApplied]
    ai_explanation: Explanation
