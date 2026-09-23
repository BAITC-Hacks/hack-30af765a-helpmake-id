import type { Advisor, DataSet, Decision, SimulationFailure, SimulationSuccess } from './types'

const base = import.meta.env.VITE_API_BASE_URL || ''

async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${base}/api/v1${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    let detail = ''
    try { const error = await response.json(); detail = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail) } catch { /* no JSON */ }
    throw new Error(`API ${response.status}${detail ? `: ${detail}` : ''}`)
  }
  return response.json() as Promise<T>
}

export const getData = () => request<DataSet>('/data')
export const simulate = (decisions: Decision[]) => request<SimulationSuccess | SimulationFailure>('/simulate', { decisions })
export const explain = (simulation_result: SimulationSuccess) => request<Advisor>('/advisor/explain', { simulation_result })
