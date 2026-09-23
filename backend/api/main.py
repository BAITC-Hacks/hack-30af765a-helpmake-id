"""Runnable stateless API for the synthetic Akim simulation."""

import os
import uuid

import fastapi
from fastapi.middleware.cors import CORSMiddleware

from .controllers import dataset
from .schemas.simulation import HealthResponse, ReadyResponse
from .v1.routers import router


def create_app() -> fastapi.FastAPI:
    dataset.load_dataset()
    app = fastapi.FastAPI(title='Akim AI Simulation API', version='1.0.0')
    local_origins = (
        'http://localhost:3000,http://localhost:5173,'
        'http://127.0.0.1:3000,http://127.0.0.1:5173'
    )
    origins = {
        origin.strip()
        for origin in os.getenv('CORS_ORIGINS', local_origins).split(',')
        if origin.strip() and origin.strip() != '*'
    }
    origins.add('https://helpmake-id.live')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(origins),
        allow_methods=['GET', 'POST'],
        allow_headers=['*'],
    )

    @app.middleware('http')
    async def request_id(request: fastapi.Request, call_next):
        supplied = request.headers.get('X-Request-ID', '')
        identifier = supplied if supplied and len(supplied) <= 128 else str(uuid.uuid4())
        response = await call_next(request)
        response.headers['X-Request-ID'] = identifier
        return response

    @app.get('/api/v1/health', summary='Liveness check', response_model=HealthResponse)
    async def health() -> dict:
        return {'status': 'ok'}

    @app.get('/api/v1/ready', summary='Dataset readiness check', response_model=ReadyResponse)
    async def ready() -> dict:
        source = dataset.load_dataset()
        return {'status': 'ok', 'dataset_version': source['version']}

    app.include_router(router)
    return app


app = create_app()
