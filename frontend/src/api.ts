import type { Advisor, DataSet, Decision, RecommendationConstraints, RecommendationGoal, RecommendationResponse, SavedScenario, ServerScenarioComparison, SimulationFailure, SimulationSuccess } from './types'

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
export const recommend = (simulation_result: SimulationSuccess, goal: RecommendationGoal, constraints: RecommendationConstraints) => request<RecommendationResponse>('/advisor/recommend', { simulation_result, goal, constraints })
export const createScenario = (name: string, decisions: Decision[]) => request<SavedScenario>('/scenarios', { name, decisions })
export const getScenario = (id: string) => request<SavedScenario>(`/scenarios/${encodeURIComponent(id)}`)
export const compareScenarios = (left_id: string, right_id: string) => request<ServerScenarioComparison>('/scenarios/compare', { left_id, right_id })
