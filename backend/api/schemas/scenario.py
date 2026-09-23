"""Public contracts for saved and compared scenarios."""

import datetime
import typing
import uuid

import pydantic

from .simulation import APIModel, CriticalPair, DecisionInput, SimulationSuccess


class ScenarioCreate(APIModel):
    name: typing.Annotated[
        str,
        pydantic.StringConstraints(
            strict=True, strip_whitespace=True, min_length=1, max_length=120
        ),
    ]
    decisions: list[DecisionInput]


class ScenarioSummary(APIModel):
    id: uuid.UUID
    name: str
    dataset_version: str
    dataset_hash: str
    score: float
    spent: int
    budget: int
    created_at: datetime.datetime


class SavedScenario(ScenarioSummary):
    decisions: list[DecisionInput]
    result: SimulationSuccess


class ScenarioCompareRequest(APIModel):
    left_id: uuid.UUID
    right_id: uuid.UUID


class DistrictDelta(APIModel):
    district_code: str
    score_delta: float
    indicator_deltas: dict[str, float]


class ScenarioComparison(APIModel):
    left: ScenarioSummary
    right: ScenarioSummary
    dataset_version: str
    dataset_hash: str
    score_delta: float
    spent_delta: int
    remaining_budget_delta: int
    districts: list[DistrictDelta]
    critical_pairs_left: list[CriticalPair]
    critical_pairs_right: list[CriticalPair]
    resolved_critical_pairs: list[CriticalPair]
    new_critical_pairs: list[CriticalPair]
