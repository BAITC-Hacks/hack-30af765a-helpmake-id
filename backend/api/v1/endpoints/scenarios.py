import uuid

import fastapi

from ... import permission
from ...controllers import scenario
from ...schemas.scenario import (
    SavedScenario,
    ScenarioCompareRequest,
    ScenarioComparison,
    ScenarioCreate,
    ScenarioSummary,
)

router = fastapi.APIRouter(prefix='/scenarios', tags=['Saved scenarios'])


@router.post(
    '',
    summary='Calculate and save a valid scenario',
    dependencies=[fastapi.Depends(permission.NoPermsRequired())],
    response_model=SavedScenario,
    response_description='Saved scenario and its calculated result',
    status_code=201,
)
async def save_scenario(request: ScenarioCreate) -> dict:
    return await scenario.create(request)


@router.get(
    '',
    summary='List saved scenarios',
    dependencies=[fastapi.Depends(permission.NoPermsRequired())],
    response_model=list[ScenarioSummary],
    response_description='Newest scenarios first',
)
async def list_scenarios(
    limit: int = fastapi.Query(50, ge=1, le=100),
    offset: int = fastapi.Query(0, ge=0),
) -> list[dict]:
    return await scenario.list_scenarios(limit, offset)


@router.post(
    '/compare',
    summary='Compare two saved scenarios from the same dataset',
    dependencies=[fastapi.Depends(permission.NoPermsRequired())],
    response_model=ScenarioComparison,
    response_description='Score, budget, district and critical-indicator differences',
    responses={
        404: {'description': 'Scenario not found'},
        409: {'description': 'Dataset mismatch'},
    },
)
async def compare_scenarios(request: ScenarioCompareRequest) -> dict:
    return await scenario.compare(request.left_id, request.right_id)


@router.get(
    '/{scenario_id}',
    summary='Get a saved scenario and its full result',
    dependencies=[fastapi.Depends(permission.NoPermsRequired())],
    response_model=SavedScenario,
    response_description='Saved scenario',
    responses={404: {'description': 'Scenario not found'}},
)
async def get_scenario(scenario_id: uuid.UUID) -> dict:
    return await scenario.get(scenario_id)


@router.delete(
    '/{scenario_id}',
    summary='Delete a saved scenario',
    dependencies=[fastapi.Depends(permission.NoPermsRequired())],
    status_code=204,
    response_class=fastapi.Response,
    responses={404: {'description': 'Scenario not found'}},
)
async def delete_scenario(scenario_id: uuid.UUID) -> None:
    await scenario.delete(scenario_id)
