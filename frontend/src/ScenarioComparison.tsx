import type { DataSet, SimulationSuccess } from './types'
import type { Slot } from './comparison'

const fmt = (value: number) => value.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const signed = (value: number) => `${value > 0 ? '+' : ''}${fmt(value)}`

function ScenarioColumn({ slot, result, data, onEdit, onNew }: {
  slot: Slot
  result: SimulationSuccess | null
  data: DataSet
  onEdit: (slot: Slot) => void
  onNew: () => void
}) {
  const districtName = (code: string) => data.districts.find(item => item.code === code)?.name || code
  const indicatorName = (id: string) => data.indicators.find(item => item.id === id)?.name || id

  return <article className="compare-column">
    <div className="compare-column-head"><span className="compare-letter">{slot}</span><div><div className="eyebrow">СОХРАНЁННЫЙ СЦЕНАРИЙ</div><h2>Сценарий {slot}</h2></div></div>
    {!result ? <div className="compare-empty"><h3>Слот {slot} пуст</h3><p>Рассчитайте пять решений и сохраните результат в этот слот.</p><button className="primary" onClick={onNew}>Создать сценарий ↗</button></div> : <>
      <div className="compare-score"><span>ASTANA QUALITY OF LIFE SCORE</span><strong>{fmt(result.score)}</strong><small>{fmt(result.baseline_score)} до решений · {signed(result.score_delta)} изменение</small></div>
      <div className="compare-metrics"><div><span>Расход бюджета</span><strong>{result.spent} / {result.budget}</strong><small>Осталось {result.remaining_budget} ед.</small></div><div><span>Критические показатели</span><strong>{result.critical_pairs_after.length}</strong><small>До решений: {result.critical_pairs_before.length}</small></div></div>
      <h3>Изменения по районам</h3><div className="compare-districts">{data.districts.map(district => { const item = result.districts.find(entry => entry.code === district.code); return <div className="compare-district" key={district.code}><span>{district.name}</span>{item ? <div><strong>{fmt(item.after.score)}</strong><small>{fmt(item.before.score)} → {fmt(item.after.score)} · {signed(item.after.score - item.before.score)}</small></div> : <strong>—</strong>}</div> })}</div>
      <h3>Оставшиеся критические показатели</h3>{result.critical_pairs_after.length ? <div className="compare-critical">{result.critical_pairs_after.map(pair => <div key={`${pair.district_code}-${pair.indicator}`}><span>{districtName(pair.district_code)} · {indicatorName(pair.indicator)}</span><strong>{fmt(pair.value)}</strong></div>)}</div> : <p className="compare-none">Нет критических сочетаний.</p>}
      <h3>Выбранные меры</h3><div className="compare-decisions">{result.decisions.map(choice => <div key={`${choice.measure_id}-${choice.district_code || 'city'}`}><b>{choice.measure_id}</b><span>{data.measures.find(item => item.id === choice.measure_id)?.name || choice.measure_id}</span><small>{choice.district_code ? districtName(choice.district_code) : 'Весь город'}</small></div>)}</div>
      <button className="secondary full" onClick={() => onEdit(slot)}>Изменить сценарий {slot} ↗</button>
    </>}
  </article>
}

export function ScenarioComparison({ data, a, b, backLabel, onBack, onNew, onEdit }: {
  data: DataSet
  a: SimulationSuccess | null
  b: SimulationSuccess | null
  backLabel: string
  onBack: () => void
  onNew: () => void
  onEdit: (slot: Slot) => void
}) {
  return <section className="comparison-page content-width">
    <div className="eyebrow">СРАВНЕНИЕ СЦЕНАРИЕВ / A · B</div>
    <div className="section-heading"><div><h1>Два решения для одного города</h1><p>Сохранённые расчёты Simulation Engine относятся к датасету {data.version}. Значения хранятся в этом браузере.</p></div><button className="secondary" onClick={onBack}>← {backLabel}</button></div>
    {a && b && <div className="compare-summary"><strong>Разница B − A:</strong><span>Score {signed(b.score - a.score)}</span><span>Расход {b.spent - a.spent > 0 ? '+' : ''}{b.spent - a.spent} ед.</span><span>Критические {b.critical_pairs_after.length - a.critical_pairs_after.length > 0 ? '+' : ''}{b.critical_pairs_after.length - a.critical_pairs_after.length}</span></div>}
    <div className="compare-grid"><ScenarioColumn slot="A" result={a} data={data} onEdit={onEdit} onNew={onNew}/><ScenarioColumn slot="B" result={b} data={data} onEdit={onEdit} onNew={onNew}/></div>
  </section>
}
