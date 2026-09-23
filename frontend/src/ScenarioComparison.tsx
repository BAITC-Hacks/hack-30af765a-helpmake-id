import type { DataSet, ServerScenarioComparison, SimulationSuccess } from './types'
import type { ServerSlotRefs, Slot } from './comparison'

const fmt = (value: number) => value.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const signed = (value: number) => `${value > 0 ? '+' : ''}${fmt(value)}`

function ScenarioColumn({ slot, result, data, serverName, onEdit, onNew }: {
  slot: Slot
  result: SimulationSuccess | null
  data: DataSet
  serverName?: string
  onEdit: (slot: Slot) => void
  onNew: () => void
}) {
  const districtName = (code: string) => data.districts.find(item => item.code === code)?.name || code
  const indicatorName = (id: string) => data.indicators.find(item => item.id === id)?.name || id

  return <article className="compare-column">
    <div className="compare-column-head"><span className="compare-letter">{slot}</span><div><div className="eyebrow">{serverName ? 'СОХРАНЕНО НА СЕРВЕРЕ' : 'ЛОКАЛЬНАЯ КОПИЯ'}</div><h2>{serverName || `Сценарий ${slot}`}</h2></div></div>
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

export function ScenarioComparison({ data, a, b, refs, serverComparison, compareLoading, compareError, backLabel, onBack, onNew, onEdit }: {
  data: DataSet
  a: SimulationSuccess | null
  b: SimulationSuccess | null
  refs: ServerSlotRefs
  serverComparison: ServerScenarioComparison | null
  compareLoading: boolean
  compareError: string
  backLabel: string
  onBack: () => void
  onNew: () => void
  onEdit: (slot: Slot) => void
}) {
  return <section className="comparison-page content-width">
    <div className="eyebrow">СРАВНЕНИЕ СЦЕНАРИЕВ / A · B</div>
    <div className="section-heading"><div><h1>Два решения для одного города</h1><p>Сценарии на датасете {data.version}. Серверные расчёты доступны после обновления страницы; ID слотов сохранены в этом браузере.</p></div><button className="secondary" onClick={onBack}>← {backLabel}</button></div>
    {refs.A && refs.B && compareLoading && <p className="compare-notice" role="status">Backend сравнивает сценарии…</p>}
    {compareError && <p className="inline-error" role="alert">Сравнение backend недоступно: {compareError}</p>}
    {a && b && (!refs.A || !refs.B) && <p className="compare-notice">Один из результатов сохранён только в браузере. Пересохраните оба слота на сервере для проверенного сравнения.</p>}
    {serverComparison && <><div className="compare-summary"><strong>Разница B − A · Simulation Engine:</strong><span>Score {signed(serverComparison.score_delta)}</span><span>Расход {serverComparison.spent_delta > 0 ? '+' : ''}{serverComparison.spent_delta} ед.</span><span>Остаток бюджета {serverComparison.remaining_budget_delta > 0 ? '+' : ''}{serverComparison.remaining_budget_delta} ед.</span></div><div className="compare-server-deltas"><strong>Изменения между сценариями по районам:</strong>{serverComparison.districts.map(item => <span key={item.district_code}>{data.districts.find(district => district.code === item.district_code)?.name || item.district_code} {signed(item.score_delta)}</span>)}</div><div className="compare-detail-grid">{serverComparison.districts.map(item => { const changed = Object.entries(item.indicator_deltas).filter(([, value]) => value !== 0); return <details key={item.district_code}><summary>{data.districts.find(district => district.code === item.district_code)?.name || item.district_code} · показатели B − A</summary>{changed.length ? <ul>{changed.map(([id, value]) => <li key={id}><span>{data.indicators.find(indicator => indicator.id === id)?.name || id}</span><strong>{signed(value)}</strong></li>)}</ul> : <p>Показатели не изменились.</p>}</details> })}</div><div className="compare-critical-change"><strong>Критические пары:</strong><span>устранено {serverComparison.resolved_critical_pairs.length}</span><span>появилось {serverComparison.new_critical_pairs.length}</span>{serverComparison.resolved_critical_pairs.map(pair => <small key={`resolved-${pair.district_code}-${pair.indicator}`}>Устранено: {data.districts.find(item => item.code === pair.district_code)?.name || pair.district_code} · {data.indicators.find(item => item.id === pair.indicator)?.name || pair.indicator}</small>)}{serverComparison.new_critical_pairs.map(pair => <small key={`new-${pair.district_code}-${pair.indicator}`}>Появилось: {data.districts.find(item => item.code === pair.district_code)?.name || pair.district_code} · {data.indicators.find(item => item.id === pair.indicator)?.name || pair.indicator}</small>)}</div></>}
    <div className="compare-grid"><ScenarioColumn slot="A" result={a} data={data} serverName={refs.A?.name} onEdit={onEdit} onNew={onNew}/><ScenarioColumn slot="B" result={b} data={data} serverName={refs.B?.name} onEdit={onEdit} onNew={onNew}/></div>
  </section>
}
