import { useState } from 'react'
import { recommend } from './api'
import type { DataSet, Decision, RecommendationGoal, RecommendationResponse, SimulationSuccess } from './types'

const goals: { id: RecommendationGoal; label: string }[] = [
  { id: 'balanced', label: 'Общий баланс' },
  { id: 'weakest_district', label: 'Слабейший район' },
  { id: 'transport', label: 'Транспорт' },
  { id: 'ecology', label: 'Экология' },
]
const fmt = (value: number) => value.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const signed = (value: number) => `${value > 0 ? '+' : ''}${fmt(value)}`

export function RecommendationPanel({ data, result, onApply }: { data: DataSet; result: SimulationSuccess; onApply: (decisions: Decision[]) => Promise<void> }) {
  const [goal, setGoal] = useState<RecommendationGoal>('balanced')
  const [target, setTarget] = useState('')
  const [maxSpent, setMaxSpent] = useState(String(result.budget))
  const [response, setResponse] = useState<RecommendationResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const measureName = (id: string) => data.measures.find(item => item.id === id)?.name || id
  const districtName = (code: string | null | undefined) => code ? data.districts.find(item => item.code === code)?.name || code : 'Весь город'

  const search = async () => {
    const cap = Number(maxSpent)
    if (!Number.isInteger(cap) || cap < 0 || cap > result.budget) { setError(`Лимит должен быть целым числом от 0 до ${result.budget}.`); return }
    setLoading(true); setError(''); setResponse(null)
    try { setResponse(await recommend(result, goal, { max_spent: cap, ...(target ? { target_district_code: target } : {}) })) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Не удалось получить рекомендации') }
    finally { setLoading(false) }
  }

  return <section className="recommend-panel">
    <div className="eyebrow">AI ADVISOR · ПРОВЕРЕННЫЕ АЛЬТЕРНАТИВЫ</div>
    <h2>Что можно улучшить?</h2>
    <p>Advisor предложит замену одной меры. Каждая альтернатива пересчитана Simulation Engine; Score и бюджет ниже получены от backend.</p>
    <div className="recommend-controls"><label>Цель<select value={goal} onChange={event => { setGoal(event.target.value as RecommendationGoal); setResponse(null) }}>{goals.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label>Район<select value={target} onChange={event => { setTarget(event.target.value); setResponse(null) }}><option value="">Весь город</option>{data.districts.map(district => <option key={district.code} value={district.code}>{district.name}</option>)}</select></label><label>Лимит расходов<input type="number" min="0" max={result.budget} step="1" value={maxSpent} onChange={event => { setMaxSpent(event.target.value); setResponse(null) }}/></label><button className="primary" disabled={loading || applying} onClick={() => void search()}>{loading ? 'Ищем…' : 'Найти альтернативы →'}</button></div>
    {error && <p className="inline-error" role="alert">{error}</p>}
    {response?.status === 'unavailable' && <p className="advisor-unavailable" role="status">Advisor недоступен: {response.reason}. Текущий числовой результат остаётся доступен.</p>}
    {response?.status === 'available' && (response.recommendations.length ? <div className="recommend-list">{response.recommendations.map((item, index) => <article className="recommend-card" key={`${item.replaces.measure_id}-${item.with_decision.measure_id}-${index}`}><div className="recommend-card-head"><b>Вариант {index + 1}</b><strong>Score {fmt(item.score)} <span>{signed(item.score_delta)} к текущему</span></strong></div><div className="recommend-swap"><div><small>ЗАМЕНИТЬ</small><strong>{item.replaces.measure_id} · {measureName(item.replaces.measure_id)}</strong><span>{districtName(item.replaces.district_code)}</span></div><b>→</b><div><small>НА</small><strong>{item.with_decision.measure_id} · {measureName(item.with_decision.measure_id)}</strong><span>{districtName(item.with_decision.district_code)}</span></div></div><p>{item.tradeoff}</p><div className="recommend-card-foot"><span>Расход {item.spent} / {result.budget} ед.</span><button className="secondary" disabled={applying} onClick={async () => { setApplying(true); try { await onApply(item.decisions) } finally { setApplying(false) } }}>{applying ? 'Пересчитываем…' : 'Применить и пересчитать ↗'}</button></div></article>)}</div> : <p className="compare-none">При этих ограничениях backend не нашёл допустимой альтернативы. Измените цель, район или лимит.</p>)}
  </section>
}
