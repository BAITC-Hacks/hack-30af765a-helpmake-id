"""Recalculate before saving and compare immutable stored results."""

import uuid

import fastapi

from .. import models
from ..schemas import scenario as schemas
from . import simulation

SUMMARY_FIELDS = (
    'id',
    'name',
    'dataset_version',
    'dataset_hash',
    'score',
    'spent',
    'budget',
    'created_at',
)


def _summary(record: dict) -> dict:
    return {field: record[field] for field in SUMMARY_FIELDS}


async def create(request: schemas.ScenarioCreate) -> dict:
    data = request.model_dump(mode='json')
    result = simulation.simulate(data['decisions'])
    if not result['valid']:
        raise fastapi.HTTPException(status_code=422, detail=result['violations'])
    return await models.scenario.create(
        {
            'name': data['name'],
            'decisions': result['decisions'],
            'dataset_version': result['dataset_version'],
            'dataset_hash': result['dataset_hash'],
            'result': result,
            'score': result['score'],
            'spent': result['spent'],
            'budget': result['budget'],
        }
    )


async def get(scenario_id: uuid.UUID) -> dict:
    record = await models.scenario.get(str(scenario_id))
    if record is None:
        raise fastapi.HTTPException(status_code=404, detail='Scenario not found.')
    return record


async def list_scenarios(limit: int, offset: int) -> list[dict]:
    return await models.scenario.list_scenarios(limit, offset)


async def delete(scenario_id: uuid.UUID) -> None:
    if not await models.scenario.delete(str(scenario_id)):
        raise fastapi.HTTPException(status_code=404, detail='Scenario not found.')


async def compare(left_id: uuid.UUID, right_id: uuid.UUID) -> dict:
    left = await get(left_id)
    right = await get(right_id)
    if (
        left['dataset_version'] != right['dataset_version']
        or left['dataset_hash'] != right['dataset_hash']
    ):
        raise fastapi.HTTPException(
            status_code=409,
            detail='Scenarios use different dataset versions or hashes and cannot be compared.',
        )
    left_districts = {item['code']: item for item in left['result']['districts']}
    right_districts = {item['code']: item for item in right['result']['districts']}
    districts = [
        {
            'district_code': code,
            'score_delta': round(
                right_districts[code]['after']['score'] - item['after']['score'], 2
            ),
            'indicator_deltas': {
                key: round(
                    right_districts[code]['after']['indicators'][key] - value,
                    4,
                )
                for key, value in item['after']['indicators'].items()
            },
        }
        for code, item in left_districts.items()
    ]
    left_critical = left['result']['critical_pairs_after']
    right_critical = right['result']['critical_pairs_after']
    left_keys = {(item['district_code'], item['indicator']) for item in left_critical}
    right_keys = {(item['district_code'], item['indicator']) for item in right_critical}
    return {
        'left': _summary(left),
        'right': _summary(right),
        'dataset_version': left['dataset_version'],
        'dataset_hash': left['dataset_hash'],
        'score_delta': round(right['score'] - left['score'], 2),
        'spent_delta': right['spent'] - left['spent'],
        'remaining_budget_delta': (right['budget'] - right['spent'])
        - (left['budget'] - left['spent']),
        'districts': districts,
        'critical_pairs_left': left_critical,
        'critical_pairs_right': right_critical,
        'resolved_critical_pairs': [
            item
            for item in left_critical
            if (item['district_code'], item['indicator']) not in right_keys
        ],
        'new_critical_pairs': [
            item
            for item in right_critical
            if (item['district_code'], item['indicator']) not in left_keys
        ],
    }
