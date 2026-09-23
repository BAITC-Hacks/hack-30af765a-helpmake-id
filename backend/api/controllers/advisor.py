"""Validate advisor input against the authoritative simulation."""

from ..webhooks import advisor as advisor_adapter
from . import simulation


async def explain(submitted: dict) -> dict:
    if not submitted['valid']:
        return {'status': 'unavailable', 'reason': 'A valid simulation result is required.'}
    current = simulation.simulate(submitted['decisions'])
    if not current['valid'] or any(
        submitted.get(field) != current.get(field)
        for field in ('dataset_hash', 'score', 'spent', 'districts', 'activated_synergies')
    ):
        return {'status': 'unavailable', 'reason': 'Simulation result is stale or altered.'}
    return await advisor_adapter.explain(current)
