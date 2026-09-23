import fastapi

from .endpoints import health


def get_router() -> fastapi.APIRouter:
    """Return the v1 API router with all registered endpoint routers."""
    router = fastapi.APIRouter()

    router.include_router(health.router, tags=['Health'])

    # Register domain routers here as they are created:
    # router.include_router(entities.router, tags=['Entities'])

    return router
