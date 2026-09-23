import type { Decision, SimulationDataResponse, SimulationResponse } from '../data/model'

const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init)
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
    const message = detail && typeof detail === 'object' && 'message' in detail
      ? String(detail.message)
      : typeof detail === 'string' ? detail : `Ошибка API (${response.status})`
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export function getSimulationData(): Promise<SimulationDataResponse> {
  return request('/simulation/data')
}

export function postSimulation(decisions: Decision[]): Promise<SimulationResponse> {
  return request('/simulation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      decisions: decisions.map((decision) => ({
        measure_id: decision.initiativeId,
        district_id: decision.districtId ?? null,
      })),
    }),
  })
}
