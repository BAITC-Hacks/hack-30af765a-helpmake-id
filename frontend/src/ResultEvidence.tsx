import type { DataSet, SimulationSuccess } from './types'

const fmt = (value: number) => value.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
const signed = (value: number) => `${value > 0 ? '+' : ''}${fmt(value)}`

export function ResultEvidence({ data, result, onEdit }: { data: DataSet; result: SimulationSuccess; onEdit: () => void }) {
  const districtName = (code: string) => data.districts.find(item => item.code === code)?.name || code
  const indicatorName = (id: string) => data.indicators.find(item => item.id === id)?.name || id
  const measureName = (id: string) => data.measures.find(item => item.id === id)?.name || id
  const strongest = [...result.districts].sort((a, b) => (b.after.score - b.before.score) - (a.after.score - a.before.score))[0]

  return <div className="evidence-section">
    <div className="block-heading"><div><div className="eyebrow">ДАННЫЕ SIMULATION ENGINE</div><h2>Основания для разбора</h2></div><button className="secondary" onClick={onEdit}>Изменить этот сценарий ↗</button></div>
    <p className="evidence-intro">Эти значения получены из ответа симулятора. Объяснение AI Advisor показано отдельно; API не связывает его фразы с отдельными фактами.</p>
    <div className="evidence-grid">
      <div className="card evidence-card"><div className="panel-title">ИТОГ И РАЙОНЫ</div><p>Score города: {fmt(result.baseline_score)} → {fmt(result.score)} ({signed(result.score_delta)}).</p><p>Самый слабый район: {districtName(result.weakest_district_before)} до решений, {districtName(result.weakest_district_after)} после.</p>{strongest && <p>Наибольшее изменение Score района: {strongest.name}, {signed(strongest.after.score - strongest.before.score)}.</p>}</div>
      <div className="card evidence-card"><div className="panel-title">РИСКИ ПО ПОКАЗАТЕЛЯМ</div><p>Критических сочетаний район × показатель: {result.critical_pairs_before.length} → {result.critical_pairs_after.length}.</p>{result.critical_pairs_after.length ? <ul>{result.critical_pairs_after.map(pair => <li key={`${pair.district_code}-${pair.indicator}`}>{districtName(pair.district_code)} · {indicatorName(pair.indicator)}: {fmt(pair.value)}</li>)}</ul> : <p>После сценария критических сочетаний нет.</p>}</div>
    </div>
    <div className="card evidence-card"><div className="panel-title">ВКЛАД ВЫБРАННЫХ МЕР</div><div className="contribution-grid">{result.measure_contributions.length ? result.measure_contributions.map(item => <div className="contribution" key={`${item.measure_id}-${item.district_code || 'city'}`}><strong>{item.measure_id} · {measureName(item.measure_id)}</strong><small>{item.district_code ? districtName(item.district_code) : 'Весь город'} · лаг {item.lag} кв. · стоимость {item.cost} ед.</small><span>{Object.entries(item.applied_effects).map(([id, value]) => `${indicatorName(id)} ${signed(value)}`).join(' · ') || 'В этом горизонте эффект не применился'}</span></div>) : <p>Backend не вернул вклад мер.</p>}</div></div>
    <div className="card evidence-card"><div className="panel-title">СИНЕРГИИ</div>{result.activated_synergies.length ? <div className="synergy-list">{result.activated_synergies.map((item, index) => <p key={`${item.district_code}-${item.indicator}-${index}`}>{item.measures.join(' + ')} · {districtName(item.district_code)} · {indicatorName(item.indicator)}: бонус {signed(item.bonus)}</p>)}</div> : <p>В этом сценарии синергии не активировались.</p>}</div>
  </div>
}
