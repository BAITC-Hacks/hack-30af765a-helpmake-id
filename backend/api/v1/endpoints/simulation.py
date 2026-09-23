import fastapi

from ... import permission
from ...controllers import simulation
from ...schemas.simulation import SimulationRequest, SimulationResponse

router = fastapi.APIRouter(prefix='/simulate', tags=['Simulation'])


@router.post(
    '',
    summary='Validate and calculate a five-decision scenario',
    dependencies=[fastapi.Depends(permission.NoPermsRequired())],
    response_model=SimulationResponse,
    response_description='Scenario validity and deterministic result',
)
async def simulate_scenario(request: SimulationRequest) -> dict:
    return simulation.simulate(request.model_dump(mode='json')['decisions'])
