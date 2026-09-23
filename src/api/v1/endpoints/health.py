import fastapi

from ....core import postgres
from ... import permission, responses, schemas

router = fastapi.APIRouter()


@router.get(
    '/health',
    summary='Health check',
    dependencies=[permission.NoPermsRequired()],
    response_model=schemas.HealthResponse,
    response_description='Application is running',
    responses=responses.gen_responses([]),
)
async def health() -> dict:
    """Return 200 while the process is alive."""
    return {'status': 'ok'}


@router.get(
    '/ready',
    summary='Readiness check',
    dependencies=[permission.NoPermsRequired()],
    response_model=schemas.ReadyResponse,
    response_description='Application is ready to serve traffic',
    responses=responses.gen_responses([responses.APIResponseInternalServerError]),
)
async def ready() -> dict:
    """Return 200 when PostgreSQL is reachable, 503 otherwise."""
    ok = await postgres.check_connection()
    if not ok:
        raise fastapi.HTTPException(
            status_code=503,
            detail={'detail': 'Database not reachable', 'database': 'unreachable'},
        )
    return {'status': 'ok', 'database': 'reachable'}
