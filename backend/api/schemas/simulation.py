"""Public contracts for the stateless Akim simulation API."""

import typing

import pydantic


class APIModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='forbid')


class HealthResponse(APIModel):
    status: typing.Literal['ok']


class ReadyResponse(HealthResponse):
    dataset_version: str


class DecisionInput(APIModel):
    measure_id: typing.Annotated[
        str, pydantic.StringConstraints(strict=True, min_length=1, max_length=8)
    ]
    district_code: (
        typing.Annotated[
            str, pydantic.StringConstraints(strict=True, min_length=1, max_length=32)
        ]
        | None
    ) = None


class SimulationRequest(APIModel):
    decisions: list[DecisionInput]


class IndicatorData(APIModel):
    id: str
    direction: str
    name: str
    description: str
    weight: float


class MapAnchor(APIModel):
    latitude: float
    longitude: float
    source: typing.Literal['illustrative_manual_anchor']


class DistrictData(APIModel):
    code: str
    name: str
    map_anchor: MapAnchor
    population_share: float
    profile: str
    indicators: dict[str, int]


class MeasureData(APIModel):
    id: str
    direction: str
    name: str
    scope: typing.Literal['district', 'city']
    cost: int
    lag: int
    effects: dict[str, int]


class SynergyRule(APIModel):
    measures: list[str]
    indicator: str
    bonus: int
    district_from: str


class IncompatibilityRule(APIModel):
    measures: list[str]
    scope: typing.Literal['global', 'same_district']
    description: str


class DatasetResponse(APIModel):
    version: str
    dataset_hash: str
    budget: int
    horizon_quarters: int
    decisions_required: int
    max_per_direction: int
    critical_threshold: int
    map_anchor_note: str
    directions: list[str]
    indicators: list[IndicatorData]
    districts: list[DistrictData]
    measures: list[MeasureData]
    synergies: list[SynergyRule]
    incompatibilities: list[IncompatibilityRule]


class Violation(APIModel):
    code: str
    message: str


class CriticalPair(APIModel):
    district_code: str
    indicator: str
    value: float


class DistrictSnapshot(APIModel):
    indicators: dict[str, float]
    score: float


class DistrictComparison(APIModel):
    code: str
    name: str
    population_share: float
    before: DistrictSnapshot
    after: DistrictSnapshot


class MeasureContribution(APIModel):
    measure_id: str
    district_code: str | None
    affected_districts: list[str]
    cost: int
    lag: int
    effect_factor: float
    full_effects: dict[str, int]
    applied_effects: dict[str, float]


class ActivatedSynergy(APIModel):
    measures: list[str]
    district_code: str
    indicator: str
    bonus: int


class QuarterDistrict(APIModel):
    district_code: str
    score: float
    indicators: dict[str, float]


class QuarterResult(APIModel):
    quarter: int
    score: float
    city_average: float
    weakest_district: str
    critical_pairs: list[CriticalPair]
    districts: list[QuarterDistrict]


class SimulationResultBase(APIModel):
    dataset_version: str
    dataset_hash: str
    budget: int
    spent: int
    remaining_budget: int
    decisions: list[DecisionInput]


class SimulationSuccess(SimulationResultBase):
    valid: typing.Literal[True]
    violations: typing.Annotated[list[Violation], pydantic.Field(max_length=0)]
    baseline_score: float
    score: float
    score_delta: float
    city_average_before: float
    city_average_after: float
    critical_pairs_before: list[CriticalPair]
    critical_pairs_after: list[CriticalPair]
    weakest_district_before: str
    weakest_district_after: str
    districts: list[DistrictComparison]
    measure_contributions: list[MeasureContribution]
    activated_synergies: list[ActivatedSynergy]
    quarters: list[QuarterResult] = pydantic.Field(default_factory=list)


class SimulationFailure(SimulationResultBase):
    valid: typing.Literal[False]
    violations: typing.Annotated[list[Violation], pydantic.Field(min_length=1)]


SimulationResponse = SimulationSuccess | SimulationFailure


class AdvisorRequest(APIModel):
    simulation_result: SimulationSuccess


class AdvisorAvailable(APIModel):
    status: typing.Literal['available']
    strengths: str
    weaknesses: str
    tradeoffs: str
    remaining_critical_indicators: str


class AdvisorUnavailable(APIModel):
    status: typing.Literal['unavailable']
    reason: str


AdvisorResponse = typing.Annotated[
    AdvisorAvailable | AdvisorUnavailable,
    pydantic.Field(discriminator='status'),
]


class RecommendationConstraints(APIModel):
    max_spent: typing.Annotated[int, pydantic.Field(strict=True, ge=0)] | None = None
    locked_measure_ids: list[str] = pydantic.Field(default_factory=list, max_length=20)
    excluded_measure_ids: list[str] = pydantic.Field(default_factory=list, max_length=20)
    target_district_code: (
        typing.Annotated[
            str, pydantic.StringConstraints(strict=True, min_length=1, max_length=32)
        ]
        | None
    ) = None


class RecommendationRequest(APIModel):
    simulation_result: SimulationSuccess
    goal: typing.Literal['transport', 'ecology', 'weakest_district', 'balanced']
    constraints: RecommendationConstraints = pydantic.Field(
        default_factory=RecommendationConstraints
    )


class Recommendation(APIModel):
    replaces: DecisionInput
    with_decision: DecisionInput
    decisions: list[DecisionInput]
    spent: int
    score: float
    score_delta: float
    tradeoff: str


class RecommendationAvailable(APIModel):
    status: typing.Literal['available']
    recommendations: list[Recommendation]


RecommendationResponse = typing.Annotated[
    RecommendationAvailable | AdvisorUnavailable,
    pydantic.Field(discriminator='status'),
]


class AskRequest(APIModel):
    simulation_result: SimulationSuccess
    question: typing.Annotated[
        str,
        pydantic.StringConstraints(
            strict=True, strip_whitespace=True, min_length=1, max_length=1000
        ),
    ]


class AskAvailable(APIModel):
    status: typing.Literal['available']
    answer: str


AskResponse = typing.Annotated[
    AskAvailable | AdvisorUnavailable,
    pydantic.Field(discriminator='status'),
]
