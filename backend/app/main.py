"""Public API for the Akim AI hackathon simulation."""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas.simulation import SimulationDataResponse
from api.schemas.simulation import SimulationRequest
from api.schemas.simulation import SimulationResponse
from app.advisor import explain
from app.simulation_engine import ScenarioError
from app.simulation_engine import get_data
from app.simulation_engine import simulate


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / '.env')

origins = [
    origin.strip()
    for origin in os.getenv(
        'FRONTEND_ORIGIN',
        'http://localhost:5173,http://localhost:5174,'
        'http://127.0.0.1:5173,http://127.0.0.1:5174',
    ).split(',')
    if origin.strip()
]

app = FastAPI(title='Akim AI Simulation API', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type'],
)


@app.get('/api/v1/health', summary='Проверка доступности API')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get(
    '/api/v1/simulation/data',
    response_model=SimulationDataResponse,
    summary='Исходные данные и каталог мер',
)
def simulation_data() -> SimulationDataResponse:
    return get_data()


@app.post(
    '/api/v1/simulation',
    response_model=SimulationResponse,
    summary='Проверить и рассчитать сценарий',
)
async def simulation(request: SimulationRequest) -> SimulationResponse:
    try:
        result = simulate(request)
    except ScenarioError as error:
        raise HTTPException(
            status_code=400,
            detail={'code': error.code, 'message': str(error)},
        ) from error
    result.ai_explanation = await explain(result)
    return result
