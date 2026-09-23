import fastapi

from ... import permission
from ...controllers import advisor
from ...schemas.simulation import (
    AdvisorRequest,
    AdvisorResponse,
    AskRequest,
    AskResponse,
    RecommendationRequest,
    RecommendationResponse,
)

router = fastapi.APIRouter(prefix='/advisor', tags=['AI advisor'])


@router.post(
    '/explain',
    summary='Explain a calculated simulation result',
    dependencies=[fastapi.Depends(permission.NoPermsRequired())],
    response_model=AdvisorResponse,
    response_description='Qualitative explanation or explicit unavailable status',
)
async def explain_scenario(request: AdvisorRequest) -> dict:
    return await advisor.explain(request.simulation_result.model_dump(mode='json'))


@router.post(
    '/recommend',
    summary='Recommend validated replacements for a calculated scenario',
    dependencies=[fastapi.Depends(permission.NoPermsRequired())],
    response_model=RecommendationResponse,
    response_description='Validated alternatives or explicit unavailable status',
)
async def recommend_scenario(request: RecommendationRequest) -> dict:
    return await advisor.recommend(
        request.simulation_result.model_dump(mode='json'),
        request.goal,
        request.constraints.model_dump(mode='json'),
    )


@router.post(
    '/ask',
    summary='Ask about a calculated scenario and the measure catalog',
    dependencies=[fastapi.Depends(permission.NoPermsRequired())],
    response_model=AskResponse,
    response_description='Grounded qualitative answer or explicit unavailable status',
)
async def ask_advisor(request: AskRequest) -> dict:
    return await advisor.ask(
        request.simulation_result.model_dump(mode='json'), request.question
    )
