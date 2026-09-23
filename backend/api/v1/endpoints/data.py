import fastapi

from ... import permission
from ...controllers import dataset
from ...schemas.simulation import DatasetResponse

router = fastapi.APIRouter(prefix='/data', tags=['Simulation data'])


@router.get(
    '',
    summary='Get the versioned baseline, measure catalog and public rules',
    dependencies=[fastapi.Depends(permission.NoPermsRequired())],
    response_model=DatasetResponse,
    response_description='Versioned simulation data',
)
async def get_simulation_data() -> dict:
    return dataset.public_data()
