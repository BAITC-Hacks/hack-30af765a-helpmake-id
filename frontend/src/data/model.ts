export type Area = 'transport' | 'environment' | 'social' | 'safety' | 'services'

export type District = {
  id: string
  name: string
  score: number
  share: number
  note: string
  location: [number, number]
  indicators: Record<string, number>
}

export type Initiative = {
  id: string
  title: string
  area: Area
  cost: number
  lag: number
  scope: 'city' | 'district'
  description: string
}

export type Decision = { initiativeId: string; districtId?: string }

export type IndicatorData = { id: string; direction: string; name: string; description: string; weight: number }
export type DistrictData = { code: string; name: string; population_share: number; profile: string; indicators: Record<string, number> }
export type MeasureData = { id: string; direction: string; name: string; scope: 'district' | 'city'; cost: number; lag: number; effects: Record<string, number> }
export type IncompatibilityData = { measures: string[]; scope: 'global' | 'same_district'; description: string }

export type SimulationDataResponse = {
  version: string
  dataset_hash: string
  budget: number
  horizon_quarters: number
  baseline_score: number
  decisions_required: number
  max_per_direction: number
  critical_threshold: number
  directions: string[]
  indicators: IndicatorData[]
  districts: DistrictData[]
  measures: MeasureData[]
  synergies: Array<{ measures: string[]; indicator: string; bonus: number; district_from: string }>
  incompatibilities: IncompatibilityData[]
}

export type SimulationSuccess = {
  valid: true
  decisions: Array<{ measure_id: string; district_code: string | null }>
  budget: number
  spent: number
  remaining_budget: number
  score: number
  baseline_score: number
  score_delta: number
  critical_pairs_before: Array<{ district_code: string; indicator: string; value: number }>
  critical_pairs_after: Array<{ district_code: string; indicator: string; value: number }>
  districts: Array<{
    code: string
    name: string
    before: { score: number; indicators: Record<string, number> }
    after: { score: number; indicators: Record<string, number> }
  }>
  activated_synergies: Array<{ measures: string[]; indicator: string; bonus: number; district_code: string }>
}
export type SimulationFailure = { valid: false; violations: Array<{ code: string; message: string }> }
export type SimulationResponse = SimulationSuccess | SimulationFailure
export type Explanation = { status: 'available' | 'unavailable'; text: string | null; reason: string | null }
export type AdvisorResponse =
  | { status: 'available'; strengths: string; weaknesses: string; tradeoffs: string; remaining_critical_indicators: string }
  | { status: 'unavailable'; reason: string }

export type SimulationResult = {
  score: number
  baselineScore: number
  spent: number
  criticalBefore: number
  criticalAfter: number
  synergies: number
  districts: Array<District & { nextScore: number; delta: number; beforeIndicators: Record<string, number>; afterIndicators: Record<string, number> }>
  explanation: Explanation
}

export type ModelData = {
  raw: SimulationDataResponse
  districts: District[]
  initiatives: Initiative[]
}

export const REQUIRED_DECISIONS = 5

export const areaLabels: Record<Area, string> = {
  transport: 'Транспорт',
  environment: 'Экология',
  social: 'Социальная сфера',
  safety: 'Безопасность',
  services: 'Городские сервисы',
}

const areaByDirection: Record<string, Area> = {
  'Транспорт': 'transport',
  'Экология': 'environment',
  'Соцсфера': 'social',
  'Безопасность': 'safety',
  'Сервисы': 'services',
}

// Only map marker locations are kept in the frontend. They are approximate.
const locations: Record<string, [number, number]> = {
  esil: [51.128, 71.43],
  almaty: [51.15, 71.49],
  saryarka: [51.18, 71.41],
  baikonur: [51.17, 71.46],
  nura: [51.155, 71.40],
}

export function adaptSimulationData(raw: SimulationDataResponse): ModelData {
  const indicatorNames = Object.fromEntries(raw.indicators.map((indicator) => [indicator.id, indicator.name]))
  const weights = Object.fromEntries(raw.indicators.map((indicator) => [indicator.id, indicator.weight]))
  const districts = raw.districts.map((district): District => ({
    id: district.code,
    name: district.name,
    score: Math.round(Object.entries(district.indicators).reduce((total, [id, value]) => total + weights[id] * value, 0) * 100) / 100,
    share: district.population_share,
    note: district.profile,
    location: locations[district.code] ?? [51.15, 71.44],
    indicators: district.indicators,
  }))
  const initiatives = raw.measures.map((measure): Initiative => ({
    id: measure.id,
    title: measure.name,
    area: areaByDirection[measure.direction],
    cost: measure.cost,
    lag: measure.lag,
    scope: measure.scope,
    description: Object.entries(measure.effects)
      .map(([id, effect]) => `${indicatorNames[id] ?? id} ${effect > 0 ? '+' : ''}${effect}`)
      .join(' · '),
  }))
  return { raw, districts, initiatives }
}

export function adaptSimulationResult(response: SimulationSuccess, districts: District[], explanation: Explanation): SimulationResult {
  return {
    score: response.score,
    baselineScore: response.baseline_score,
    spent: response.spent,
    criticalBefore: response.critical_pairs_before.length,
    criticalAfter: response.critical_pairs_after.length,
    synergies: response.activated_synergies.length,
    explanation,
    districts: response.districts.map((comparison) => {
      const district = districts.find((item) => item.id === comparison.code)!
      return {
        ...district,
        nextScore: comparison.after.score,
        delta: Math.round((comparison.after.score - comparison.before.score) * 100) / 100,
        beforeIndicators: comparison.before.indicators,
        afterIndicators: comparison.after.indicators,
      }
    }),
  }
}
