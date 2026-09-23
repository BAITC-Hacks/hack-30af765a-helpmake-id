import type { SimulationSuccess } from './types'

export type Slot = 'A' | 'B'
export type ComparisonSlots = Record<Slot, SimulationSuccess | null>

const key = 'akim-ai-comparison-v1'
const empty = (): ComparisonSlots => ({ A: null, B: null })

function isResult(value: unknown): value is SimulationSuccess {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<SimulationSuccess>
  return candidate.valid === true && typeof candidate.dataset_hash === 'string' &&
    typeof candidate.score === 'number' && typeof candidate.spent === 'number' &&
    Array.isArray(candidate.districts) && Array.isArray(candidate.critical_pairs_after) &&
    Array.isArray(candidate.decisions)
}

export function loadComparison(): ComparisonSlots {
  try {
    const stored = JSON.parse(localStorage.getItem(key) || 'null') as Partial<ComparisonSlots> | null
    return { A: isResult(stored?.A) ? stored.A : null, B: isResult(stored?.B) ? stored.B : null }
  } catch { return empty() }
}

export function saveComparison(slots: ComparisonSlots): void {
  try { localStorage.setItem(key, JSON.stringify(slots)) } catch { /* Browsers may disable storage. In-memory slots still work. */ }
}

export function forDataset(slots: ComparisonSlots, datasetHash: string): ComparisonSlots {
  return {
    A: slots.A?.dataset_hash === datasetHash ? slots.A : null,
    B: slots.B?.dataset_hash === datasetHash ? slots.B : null,
  }
}
