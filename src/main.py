"""Application entry point.

Start with:
    uvicorn src.main:app --reload
"""

import contextlib
import logging
import time
import uuid

import fastapi
import fastapi.middleware.cors
import fastapi.responses

from src.api import exceptions as app_exceptions
from src.api.v1 import routers
from src.core import config, http_client, postgres
from src.core import logging as app_logging

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    app_logging.configure_logging()
    logger.info('Starting up')

    await postgres.on_startup()
    await http_client.on_startup()

    yield

    logger.info('Shutting down')
    await http_client.on_shutdown()
    await postgres.on_shutdown()


def create_app() -> fastapi.FastAPI:
    settings = config.get_settings()

    app = fastapi.FastAPI(
        title=settings.APP_NAME,
        version='0.1.0',
        docs_url='/docs',
        redoc_url='/redoc',
        openapi_url='/openapi.json',
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────

    app.add_middleware(
        fastapi.middleware.cors.CORSMiddleware,
        allow_origins=settings.cors_origins_list(),
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.middleware('http')
    async def request_id_middleware(
        request: fastapi.Request,
        call_next,
    ) -> fastapi.Response:
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception as exc:
            # Starlette's BaseHTTPMiddleware re-raises unhandled exceptions
            # even after inner exception handlers have processed them.
            logger.exception('Unhandled exception propagated to middleware: %s', exc)
            return fastapi.responses.JSONResponse(
                status_code=500,
                content={'detail': 'Internal server error'},
                headers={'X-Request-ID': request_id},
            )
        response.headers['X-Request-ID'] = request_id
        return response

    @app.middleware('http')
    async def logging_middleware(
        request: fastapi.Request,
        call_next,
    ) -> fastapi.Response:
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            response = fastapi.responses.JSONResponse(status_code=500, content={})
        duration_ms = round((time.monotonic() - start) * 1000, 2)
        request_id = getattr(request.state, 'request_id', '')
        logger.info(
            '%s %s %s %.2fms',
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
                'request_id': request_id,
            },
        )
        return response

    # ── Exception handlers ────────────────────────────────────────────────────

    @app.exception_handler(app_exceptions.AppException)
    async def app_exception_handler(
        request: fastapi.Request,
        exc: app_exceptions.AppException,
    ) -> fastapi.responses.JSONResponse:
        return fastapi.responses.JSONResponse(
            status_code=exc.status_code,
            content=exc.response_body(),
            headers={'X-Request-ID': getattr(request.state, 'request_id', '')},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: fastapi.Request,
        exc: Exception,
    ) -> fastapi.responses.JSONResponse:
        logger.exception('Unhandled exception: %s', exc)
        return fastapi.responses.JSONResponse(
            status_code=500,
            content={'detail': 'Internal server error'},
            headers={'X-Request-ID': getattr(request.state, 'request_id', '')},
        )

    # ── Routers ───────────────────────────────────────────────────────────────

    app.include_router(
        routers.get_router(),
        prefix=settings.API_V1_PREFIX,
    )

    return app


app = create_app()
