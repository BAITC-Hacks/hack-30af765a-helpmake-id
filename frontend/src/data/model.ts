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
export type DistrictData = { id: string; population_share: number; profile: string; indicators: Record<string, number>; expected_score: number }
export type MeasureData = { id: string; direction: string; name: string; type: 'Район' | 'Город'; cost: number; lag: number; effects: Record<string, number> }
export type IncompatibilityData = { measures: string[]; scope: 'global' | 'same_district'; description: string }

export type SimulationDataResponse = {
  budget: number
  horizon_quarters: number
  baseline_score: number
  directions: string[]
  indicators: IndicatorData[]
  districts: DistrictData[]
  measures: MeasureData[]
  synergies: Array<{ measures: string[]; indicator: string; bonus: number; district_from: string }>
  incompatibilities: IncompatibilityData[]
}

export type SimulationResponse = {
  decisions: Array<{ measure_id: string; district_id: string | null }>
  budget: number
  spent: number
  remaining_budget: number
  score: number
  baseline_score: number
  score_delta: number
  city_score_before: number
  city_score_after: number
  weakest_district_score_before: number
  weakest_district_score_after: number
  critical_pairs_before: number
  critical_pairs_after: number
  districts: Array<{
    district_id: string
    before: { district_score: number; indicators: Record<string, number> }
    after: { district_score: number; indicators: Record<string, number> }
  }>
  activated_synergies: Array<{ measures: string[]; indicator: string; bonus: number; district_id: string }>
  ai_explanation: { status: 'available' | 'unavailable'; text: string | null; reason: string | null }
}

export type SimulationResult = {
  score: number
  baselineScore: number
  spent: number
  criticalBefore: number
  criticalAfter: number
  synergies: number
  districts: Array<District & { nextScore: number; delta: number; beforeIndicators: Record<string, number>; afterIndicators: Record<string, number> }>
  explanation: SimulationResponse['ai_explanation']
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
  'Есиль': [51.128, 71.43],
  'Алматы': [51.15, 71.49],
  'Сарыарка': [51.18, 71.41],
  'Байконур': [51.17, 71.46],
  'Нура': [51.155, 71.40],
}

export function adaptSimulationData(raw: SimulationDataResponse): ModelData {
  const indicatorNames = Object.fromEntries(raw.indicators.map((indicator) => [indicator.id, indicator.name]))
  const districts = raw.districts.map((district): District => ({
    id: district.id,
    name: district.id,
    score: district.expected_score,
    share: district.population_share,
    note: district.profile,
    location: locations[district.id] ?? [51.15, 71.44],
    indicators: district.indicators,
  }))
  const initiatives = raw.measures.map((measure): Initiative => ({
    id: measure.id,
    title: measure.name,
    area: areaByDirection[measure.direction],
    cost: measure.cost,
    lag: measure.lag,
    scope: measure.type === 'Город' ? 'city' : 'district',
    description: Object.entries(measure.effects)
      .map(([id, effect]) => `${indicatorNames[id] ?? id} ${effect > 0 ? '+' : ''}${effect}`)
      .join(' · '),
  }))
  return { raw, districts, initiatives }
}

export function adaptSimulationResult(response: SimulationResponse, districts: District[]): SimulationResult {
  return {
    score: response.score,
    baselineScore: response.baseline_score,
    spent: response.spent,
    criticalBefore: response.critical_pairs_before,
    criticalAfter: response.critical_pairs_after,
    synergies: response.activated_synergies.length,
    explanation: response.ai_explanation,
    districts: response.districts.map((comparison) => {
      const district = districts.find((item) => item.id === comparison.district_id)!
      return {
        ...district,
        nextScore: comparison.after.district_score,
        delta: Math.round((comparison.after.district_score - comparison.before.district_score) * 100) / 100,
        beforeIndicators: comparison.before.indicators,
        afterIndicators: comparison.after.indicators,
      }
    }),
  }
}
