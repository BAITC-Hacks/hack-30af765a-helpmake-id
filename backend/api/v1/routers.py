import fastapi

from .endpoints import advisor, data, scenarios, simulation

router = fastapi.APIRouter(prefix='/api/v1')
router.include_router(data.router)
router.include_router(simulation.router)
router.include_router(advisor.router)
router.include_router(scenarios.router)
