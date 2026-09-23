import type { AdvisorResponse, Decision, Explanation, SimulationDataResponse, SimulationResponse, SimulationSuccess } from '../data/model'

const API_URL = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')

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
  return request('/data')
}

export async function postSimulation(decisions: Decision[]): Promise<{ simulation: SimulationSuccess; explanation: Explanation }> {
  const simulation = await request<SimulationResponse>('/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      decisions: decisions.map((decision) => ({
        measure_id: decision.initiativeId,
        district_code: decision.districtId ?? null,
      })),
    }),
  })
  if (!simulation.valid) throw new Error(simulation.violations.map((item) => item.message).join(' '))

  let explanation: Explanation
  try {
    const advisor = await request<AdvisorResponse>('/advisor/explain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulation_result: simulation }),
    })
    explanation = advisor.status === 'available'
      ? { status: 'available', text: [advisor.strengths, advisor.weaknesses, advisor.tradeoffs, advisor.remaining_critical_indicators].filter(Boolean).join('\n\n'), reason: null }
      : { status: 'unavailable', text: null, reason: advisor.reason }
  } catch {
    explanation = { status: 'unavailable', text: null, reason: 'AI Advisor временно недоступен. Числовой результат рассчитан сервером.' }
  }
  return { simulation, explanation }
}
