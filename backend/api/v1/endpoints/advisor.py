import fastapi

from ... import permission
from ...controllers import advisor
from ...schemas.simulation import AdvisorRequest, AdvisorResponse

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
