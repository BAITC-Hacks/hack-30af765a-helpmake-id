import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { explain, getData, simulate } from './api'
import type { Advisor, CriticalPair, DataSet, Decision, District, Measure, Quarter, SimulationSuccess } from './types'
import './styles.css'

type Page = 'welcome' | 'center' | 'decisions' | 'result' | 'map'
const fmt = (value: number, digits = 1) => value.toLocaleString('ru-RU', { minimumFractionDigits: digits, maximumFractionDigits: digits })
const signed = (value: number) => `${value > 0 ? '+' : ''}${fmt(value)}`

function localIssues(data: DataSet, choices: Decision[]) {
  const issues: string[] = []
  if (choices.length > data.decisions_required) issues.push(`Можно выбрать только ${data.decisions_required} решений.`)
  const chosen = choices.map(choice => data.measures.find(measure => measure.id === choice.measure_id)).filter((measure): measure is Measure => !!measure)
  if (new Set(choices.map(choice => choice.measure_id)).size !== choices.length) issues.push('Одну меру можно выбрать только один раз.')
  if (chosen.reduce((sum, measure) => sum + measure.cost, 0) > data.budget) issues.push('Стоимость превышает бюджет.')
  for (const direction of data.directions) if (chosen.filter(measure => measure.direction === direction).length > data.max_per_direction) issues.push(`В направлении «${direction}» максимум ${data.max_per_direction} меры.`)
  for (const rule of data.incompatibilities) {
    const a = choices.find(choice => choice.measure_id === rule.measures[0])
    const b = choices.find(choice => choice.measure_id === rule.measures[1])
    if (a && b && (rule.scope === 'global' || a.district_code === b.district_code)) issues.push(rule.description)
  }
  return issues
}

// /data has no baseline Score. Ask the engine for one valid scenario and use only its baseline_score.
function baselineProbe(data: DataSet): Decision[] | null {
  const measures = [...data.measures].sort((a, b) => a.cost - b.cost)
  const firstDistrict = data.districts[0]?.code
  const search = (start: number, choices: Decision[]): Decision[] | null => {
    if (choices.length === data.decisions_required) return localIssues(data, choices).length ? null : choices
    for (let i = start; i < measures.length; i++) {
      const measure = measures[i]
      if (measure.scope === 'district' && !firstDistrict) continue
      const next = [...choices, { measure_id: measure.id, ...(measure.scope === 'district' ? { district_code: firstDistrict } : {}) }]
      if (localIssues(data, next).length) continue
      const found = search(i + 1, next)
      if (found) return found
    }
    return null
  }
  return search(0, [])
}

function App() {
  const [data, setData] = useState<DataSet | null>(null)
  const [loadError, setLoadError] = useState('')
  const [loading, setLoading] = useState(true)
  const [baseline, setBaseline] = useState<number | null>(null)
  const [page, setPage] = useState<Page>('welcome')
  const [districtCode, setDistrictCode] = useState('')
  const [filter, setFilter] = useState('Все')
  const [choices, setChoices] = useState<Decision[]>([])
  const [result, setResult] = useState<SimulationSuccess | null>(null)
  const [violations, setViolations] = useState<string[]>([])
  const [runError, setRunError] = useState('')
  const [running, setRunning] = useState(false)
  const [advisor, setAdvisor] = useState<Advisor | null>(null)
  const [advisorError, setAdvisorError] = useState('')
  const [advisorLoading, setAdvisorLoading] = useState(false)
  const [quarterIndex, setQuarterIndex] = useState(8)

  const reload = async () => {
    setLoading(true); setLoadError(''); setBaseline(null)
    try {
      const loaded = await getData()
      setData(loaded)
      setDistrictCode(current => loaded.districts.some(item => item.code === current) ? current : loaded.districts[0]?.code || '')
      const probe = baselineProbe(loaded)
      if (probe) {
        try { const response = await simulate(probe); if (response.valid) setBaseline(response.baseline_score) } catch { /* baseline stays unavailable */ }
      }
    } catch (error) { setLoadError(error instanceof Error ? error.message : 'Не удалось загрузить данные') }
    finally { setLoading(false) }
  }
  useEffect(() => { void reload() }, [])

  const selectedDistrict = data?.districts.find(item => item.code === districtCode)
  const spent = data ? choices.reduce((sum, choice) => sum + (data.measures.find(measure => measure.id === choice.measure_id)?.cost || 0), 0) : 0
  const issues = data ? localIssues(data, choices) : []
  const canRun = !!data && choices.length === data.decisions_required && issues.length === 0 && !running
  const critical = data && selectedDistrict ? data.indicators.filter(indicator => selectedDistrict.indicators[indicator.id] < data.critical_threshold) : []
  const weakest = data && selectedDistrict ? [...data.indicators].sort((a, b) => selectedDistrict.indicators[a.id] - selectedDistrict.indicators[b.id]).slice(0, 3) : []
  const quarter = result?.quarters.find(item => item.quarter === quarterIndex)

  const choose = (measure: Measure) => {
    if (!data) return
    const existing = choices.find(choice => choice.measure_id === measure.id)
    if (existing) { setChoices(choices.filter(choice => choice.measure_id !== measure.id)); return }
    const next: Decision = { measure_id: measure.id, ...(measure.scope === 'district' ? { district_code: districtCode } : {}) }
    if (choices.length >= data.decisions_required || localIssues(data, [...choices, next]).length) return
    setChoices([...choices, next]); setViolations([]); setRunError('')
  }
  const changeDistrict = (measureId: string, code: string) => {
    if (!data) return
    const next = choices.map(choice => choice.measure_id === measureId ? { ...choice, district_code: code } : choice)
    setChoices(next); setViolations([])
  }
  const run = async () => {
    if (!canRun) return
    setRunning(true); setRunError(''); setViolations([]); setAdvisor(null); setAdvisorError('')
    try {
      const response = await simulate(choices)
      if (!response.valid) { setViolations(response.violations.map(item => item.message)); return }
      setResult(response); setQuarterIndex(response.quarters.at(-1)?.quarter ?? 8); setPage('result')
      setAdvisorLoading(true)
      try { setAdvisor(await explain(response)) }
      catch (error) { setAdvisorError(error instanceof Error ? error.message : 'Не удалось загрузить объяснение') }
      finally { setAdvisorLoading(false) }
    } catch (error) { setRunError(error instanceof Error ? error.message : 'Ошибка расчёта') }
    finally { setRunning(false) }
  }
  const reset = () => { setChoices([]); setResult(null); setAdvisor(null); setViolations([]); setRunError(''); setPage('center') }

  if (loading) return <div className="fullscreen-state"><span className="brand-mark">A<span>•</span></span><div className="spinner"/><h1>Загружаем ситуационный центр</h1><p>Получаем районы, показатели и меры из API</p></div>
  if (!data) return <div className="fullscreen-state"><span className="brand-mark">A<span>•</span></span><h1>Данные города недоступны</h1><p>{loadError}</p><button className="primary" onClick={() => void reload()}>Повторить загрузку →</button></div>
  if (!data.districts.length || !data.indicators.length || !data.measures.length) return <div className="fullscreen-state"><span className="brand-mark">A<span>•</span></span><h1>Пока нет данных для сценария</h1><p>API вернул пустой список районов, показателей или мер.</p><button className="primary" onClick={() => void reload()}>Проверить снова →</button></div>

  return <div className="app-shell">
    <header className="topbar"><button className="brand" onClick={() => setPage('welcome')}><span className="brand-mark">A<span>•</span></span><span>AKIM AI<small>СИТУАЦИОННЫЙ ЦЕНТР</small></span></button><div className="topnav"><span>СИМУЛЯТОР ГОРОДА</span><span> / </span><strong>{page === 'welcome' ? 'Старт' : page === 'center' ? 'Обзор города' : page === 'decisions' ? 'Пять решений' : 'Результат'}</strong></div><div className="topright"><span className="live-dot"/> Dataset {data.version}<span className="top-divider"/> Бюджет {data.budget} ед.</div></header>
    <main>
      {page === 'welcome' && <section className="welcome content-width"><div className="eyebrow">ГЛАВНЫЙ ЭКРАН / 01</div><div className="welcome-grid"><div><h1>Вы — аким.<br/>У вас {data.budget} единиц<br/>и {data.decisions_required} решений.</h1><p>Распределите ограниченный бюджет между районами. Посмотрите последствия для города через {data.horizon_quarters} кварталов и разберитесь, почему меняется оценка.</p><button className="primary" onClick={() => setPage('center')}>Начать игру <span>↗</span></button><div className="micro">1 ход · {data.decisions_required} мер · {data.horizon_quarters} кварталов последствий</div></div><div className="welcome-card"><div className="eyebrow">СИТУАЦИЯ СЕЙЧАС</div><h2>Пять районов. Один бюджет.</h2><DistrictMap districts={data.districts} selected={districtCode} onSelect={setDistrictCode} note={data.map_anchor_note}/><div className="welcome-stat"><span>БАЗОВЫЙ SCORE</span><strong>{baseline === null ? '—' : fmt(baseline, 2)}</strong><small>{baseline === null ? 'Ожидаем расчёт backend' : 'Из ответа Simulation Engine'}</small></div></div></div><div className="steps"><span>01&nbsp; Изучите районы</span><span>02&nbsp; Примите {data.decisions_required} решений</span><span>03&nbsp; Разберите эффект</span></div></section>}
      {page === 'center' && <section className="dashboard content-width"><div className="section-heading"><div><div className="eyebrow">РАЙОНЫ ГОРОДА / 02</div><h1>Астана. Пять районов сценария.</h1><p>Выберите район на схеме, затем изучите показатели и проблемные места.</p></div><button className="primary" onClick={() => setPage('decisions')}>Создать сценарий ↗</button></div><div className="center-grid"><aside className="district-list"><div className="panel-title">РАЙОНЫ ГОРОДА</div>{data.districts.map(district => <button className={`district-item ${districtCode === district.code ? 'active' : ''}`} key={district.code} onClick={() => setDistrictCode(district.code)}><span><strong>{district.name}</strong><small>{district.profile}</small></span><b>{district.indicators ? Math.min(...Object.values(district.indicators)) : '—'}</b></button>)}<div className="mini-metrics"><div><span>БАЗОВЫЙ SCORE</span><strong>{baseline === null ? '—' : fmt(baseline, 2)}</strong></div><div><span>БЮДЖЕТ</span><strong>{data.budget}</strong></div><div><span>РЕШЕНИЯ</span><strong>{choices.length}/{data.decisions_required}</strong></div></div></aside><div className="map-panel"><div className="panel-title">КАРТА И ПОКАЗАТЕЛИ <span>Выберите район · условные точки</span></div><DistrictMap districts={data.districts} selected={districtCode} onSelect={setDistrictCode} note={data.map_anchor_note}/><div className="map-foot">● Условные точки из API · не являются границами районов</div></div><aside className="insight-panel"><div className="panel-title">В ФОКУСЕ / {selectedDistrict?.name.toUpperCase()}</div><h2>{selectedDistrict?.profile}</h2><div className="insight-box"><span>КРИТИЧЕСКИЕ ПОКАЗАТЕЛИ</span>{critical?.length ? critical.map(item => <div className="critical-row" key={item.id}><span>{item.name}</span><b>{selectedDistrict?.indicators[item.id]}/100</b></div>) : <p>Показателей ниже {data.critical_threshold} нет.</p>}</div><div className="insight-box soft"><span>НИЗКИЕ ПОКАЗАТЕЛИ</span>{weakest.map(item => <div className="critical-row" key={item.id}><span>{item.name}</span><b>{selectedDistrict?.indicators[item.id]}</b></div>)}</div><button className="secondary full" onClick={() => setPage('decisions')}>Подобрать меры для города →</button></aside></div><div className="indicator-grid">{data.indicators.map(indicator => <div className="indicator-tile" key={indicator.id}><span>{indicator.id} · {indicator.direction}</span><strong>{selectedDistrict?.indicators[indicator.id]}</strong><div className="bar"><i style={{ width: `${selectedDistrict?.indicators[indicator.id] || 0}%` }}/></div><small>{indicator.name}</small></div>)}</div></section>}
      {page === 'decisions' && <section className="decisions-layout content-width"><aside className="selection-rail"><div className="eyebrow">ВАШ ПЛАН</div><h2>{choices.length} {choices.length === 1 ? 'решение' : 'решений'}</h2><p>из {data.decisions_required} необходимых</p><div className="budget-number">{spent} <span>/ {data.budget}</span></div><div className="bar budget-bar"><i style={{ width: `${Math.min(100, spent / data.budget * 100)}%` }}/></div><small>Использовано {spent} ед. · осталось {data.budget - spent} ед.</small><div className="selected-list">{choices.length ? choices.map((choice, index) => { const measure = data.measures.find(item => item.id === choice.measure_id)!; return <div className="selected-card" key={choice.measure_id}><div><b>{String(index + 1).padStart(2, '0')}</b><strong>{measure.name}</strong><button aria-label={`Убрать ${measure.name}`} onClick={() => choose(measure)}>×</button></div><small>{measure.id} · {measure.cost} ед. · {measure.scope === 'city' ? 'весь город' : data.districts.find(item => item.code === choice.district_code)?.name}</small>{measure.scope === 'district' && <select aria-label={`Район для ${measure.name}`} value={choice.district_code} onChange={event => changeDistrict(measure.id, event.target.value)}>{data.districts.map(district => <option value={district.code} key={district.code}>{district.name}</option>)}</select>}</div> }) : <div className="empty-selection">Выберите меры в каталоге справа.</div>}</div><button className="text-button" onClick={() => setPage('center')}>← К обзору города</button></aside><div className="catalog"><div className="eyebrow">СЦЕНАРИЙ / ВЫБОР РЕШЕНИЙ</div><h1>Что вы измените за {data.horizon_quarters} кварталов?</h1><p>Выбирайте меры для районов или всего города. Ограничения проверит backend.</p><div className="catalog-toolbar"><label>Район для мер <select value={districtCode} onChange={event => setDistrictCode(event.target.value)}>{data.districts.map(district => <option value={district.code} key={district.code}>{district.name}</option>)}</select></label><div className="filters">{['Все', ...data.directions].map(direction => <button className={filter === direction ? 'active' : ''} onClick={() => setFilter(direction)} key={direction}>{direction}</button>)}</div></div><div className="measure-list">{data.measures.filter(measure => filter === 'Все' || filter === measure.direction).map(measure => { const selected = choices.some(choice => choice.measure_id === measure.id); const next = [...choices, { measure_id: measure.id, ...(measure.scope === 'district' ? { district_code: districtCode } : {}) }]; const blocked = !selected && (choices.length >= data.decisions_required || localIssues(data, next).length > 0); return <div className={`measure-card ${selected ? 'selected' : ''}`} key={measure.id}><div className="measure-top"><span className="measure-id">{measure.id}</span><span>{measure.direction}</span><span>{measure.scope === 'city' ? 'Весь город' : selected ? data.districts.find(item => item.code === choices.find(choice => choice.measure_id === measure.id)?.district_code)?.name : selectedDistrict?.name}</span></div><h3>{measure.name}</h3><div className="effect-tags">{Object.entries(measure.effects).map(([id, value]) => <span key={id}>{data.indicators.find(item => item.id === id)?.name || id} <b>{value > 0 ? '+' : ''}{value}</b></span>)}</div><div className="measure-bottom"><span>{measure.cost} ед. <em>· лаг {measure.lag} кв.</em></span><button className={selected ? 'remove-choice' : 'add-choice'} disabled={blocked} onClick={() => choose(measure)}>{selected ? 'Убрать' : blocked ? 'Недоступно' : 'Добавить +'}</button></div></div> })}</div></div><aside className="guidance"><div className="eyebrow">ПОМОЩЬ С РЕШЕНИЕМ</div><h2>Сначала причина, потом действие.</h2><p>У Нуры и других районов разные проблемные места. Сравните исходные показатели перед выбором.</p><div className="guidance-box"><b>ОГРАНИЧЕНИЯ</b><ul><li>Ровно {data.decisions_required} решений</li><li>Бюджет не выше {data.budget}</li><li>Не более {data.max_per_direction} мер в одном направлении</li><li>Несовместимые меры нельзя объединять</li></ul></div>{issues.map(issue => <p className="inline-error" key={issue}>{issue}</p>)}{violations.map(issue => <p className="inline-error" key={issue}>{issue}</p>)}{runError && <p className="inline-error" role="alert">{runError}</p>}<button className="primary full" disabled={!canRun} onClick={() => void run()}>{running ? 'Рассчитываем…' : 'SIMULATE →'}</button><small>Итоговый Score рассчитывает только backend.</small></aside><div className="mobile-run"><span>{choices.length}/{data.decisions_required} мер · {spent}/{data.budget} ед.</span><button className="primary" disabled={!canRun} onClick={() => void run()}>{running ? 'Расчёт…' : 'SIMULATE →'}</button></div></section>}
      {result && page === 'result' && <section className="result-page content-width"><div className="eyebrow">РЕЗУЛЬТАТ СИМУЛЯЦИИ / 04</div><div className="section-heading"><div><h1>Как {result.decisions.length} мер меняют город</h1><p>{result.dataset_version} · расчёт Simulation Engine · горизонт Q0–Q{data.horizon_quarters}</p></div><button className="secondary" onClick={reset}>Новый сценарий ↗</button></div><div className="result-grid"><div><div className="score-panel"><div className="eyebrow">ИНДЕКС ГОРОДА</div><div className="score-row"><div><strong>{fmt(result.baseline_score, 2)}</strong><span>ДО РЕШЕНИЙ</span></div><b>→</b><div><strong>{fmt(result.score, 2)}</strong><span>ПОСЛЕ РЕШЕНИЙ</span></div><div className="score-delta">{signed(result.score_delta)}<small>к базовому Score</small></div></div><p>Средний показатель города: {fmt(result.city_average_before, 2)} → {fmt(result.city_average_after, 2)}. Потрачено {result.spent} из {result.budget} ед.</p></div><div className="block-heading"><h2>Районы · до и после</h2><button className="text-button" onClick={() => setPage('map')}>Посмотреть на карте →</button></div>{result.districts.length ? <div className="district-results">{result.districts.map(district => <button key={district.code} onClick={() => { setDistrictCode(district.code); setPage('map') }}><span>{district.name}</span><strong>{fmt(district.before.score, 2)} → {fmt(district.after.score, 2)}</strong><em>{signed(district.after.score - district.before.score)}</em></button>)}</div> : <div className="empty-selection">Backend не вернул результаты по районам.</div>}<div className="two-columns"><div className="card"><div className="panel-title">КРИТИЧЕСКИЕ ПОКАЗАТЕЛИ</div><p>До: {result.critical_pairs_before.length} · После: {result.critical_pairs_after.length}</p><CriticalList pairs={result.critical_pairs_after} data={data}/></div><div className="card"><div className="panel-title">ВАШИ РЕШЕНИЯ</div>{result.decisions.map(choice => { const measure = data.measures.find(item => item.id === choice.measure_id); return <div className="choice-summary" key={choice.measure_id}><b>{choice.measure_id}</b><span>{measure?.name}</span><small>{choice.district_code ? data.districts.find(item => item.code === choice.district_code)?.name : 'Весь город'}</small></div> })}</div></div></div><aside className="advisor-panel"><div className="eyebrow">✦ AI ADVISOR</div><h2>Где выигрыш,<br/>а где риск?</h2>{advisorLoading && <p>Готовим объяснение…</p>}{advisor?.status === 'available' && <div className="advisor-copy"><div><b>Сильные стороны</b><p>{advisor.strengths}</p></div><div><b>Слабые стороны</b><p>{advisor.weaknesses}</p></div><div><b>Компромиссы</b><p>{advisor.tradeoffs}</p></div><div><b>Оставшиеся критические показатели</b><p>{advisor.remaining_critical_indicators}</p></div></div>}{advisor?.status === 'unavailable' && <div className="advisor-unavailable"><b>AI Advisor недоступен</b><p>{advisor.reason}</p><small>Числовой результат и поквартальная динамика доступны.</small></div>}{advisorError && <div className="advisor-unavailable" role="alert"><b>Не удалось получить объяснение</b><p>{advisorError}</p><small>Расчёт остаётся доступен.</small></div>}<button className="primary full" onClick={() => setPage('map')}>Посмотреть динамику →</button></aside></div></section>}
      {result && page === 'map' && <section className="map-result content-width"><div className="section-heading"><div><div className="eyebrow">ПОСЛЕДСТВИЯ / Q{quarter?.quarter ?? quarterIndex}</div><h1>Карта последствий: что изменилось?</h1><p>Нажмите на район и квартал, чтобы сравнить значения.</p></div><button className="secondary" onClick={() => setPage('result')}>← К результату</button></div><div className="center-grid"><aside className="district-list"><div className="panel-title">РАЙОНЫ · ДО / Q{quarter?.quarter}</div>{result.districts.map(district => { const current = quarter?.districts.find(item => item.district_code === district.code); return <button className={`district-item ${districtCode === district.code ? 'active' : ''}`} key={district.code} onClick={() => setDistrictCode(district.code)}><span><strong>{district.name}</strong><small>{fmt(district.before.score, 2)} → {current ? fmt(current.score, 2) : '—'}</small></span><b>{current ? signed(current.score - district.before.score) : '—'}</b></button> })}<div className="mini-metrics"><div><span>ИНДЕКС ГОРОДА</span><strong>{fmt(result.baseline_score, 2)} → {quarter ? fmt(quarter.score, 2) : '—'}</strong></div></div></aside><div className="map-panel"><div className="panel-title">УСЛОВНАЯ КАРТА РАЙОНОВ <span>Q{quarter?.quarter ?? '—'}</span></div><DistrictMap districts={data.districts} selected={districtCode} onSelect={setDistrictCode} note={data.map_anchor_note} values={quarter}/><div className="timeline"><div className="panel-title">ДИНАМИКА ПО КВАРТАЛАМ</div><div className="quarter-buttons">{result.quarters.length ? result.quarters.map(item => <button className={quarterIndex === item.quarter ? 'active' : ''} onClick={() => setQuarterIndex(item.quarter)} key={item.quarter}>Q{item.quarter}<span>{fmt(item.score, 2)}</span></button>) : <p>Поквартальные данные не вернулись.</p>}</div></div></div><aside className="insight-panel"><div className="panel-title">ДЕТАЛИ / {selectedDistrict?.name.toUpperCase()}</div><h2>Показатели района</h2>{data.indicators.map(indicator => { const before = result.districts.find(item => item.code === districtCode)?.before.indicators[indicator.id]; const after = quarter?.districts.find(item => item.district_code === districtCode)?.indicators[indicator.id]; return <div className="indicator-comparison" key={indicator.id}><span>{indicator.name}</span><b>{before === undefined ? '—' : fmt(before)} → {after === undefined ? '—' : fmt(after)}</b><em>{before === undefined || after === undefined ? '—' : signed(after - before)}</em></div> })}<div className="insight-box soft"><span>КРИТИЧЕСКИЕ В Q{quarter?.quarter}</span><CriticalList pairs={quarter?.critical_pairs.filter(item => item.district_code === districtCode) || []} data={data}/></div></aside></div></section>}
    </main><footer><span>AKIM AI · CITY DECISION SIMULATOR</span><span>Синтетические данные · не прогноз реальных городских последствий</span></footer>
  </div>
}

function CriticalList({ pairs, data }: { pairs: CriticalPair[]; data: DataSet }) { return pairs.length ? <div className="critical-list">{pairs.map(pair => <div className="critical-row" key={`${pair.district_code}-${pair.indicator}`}><span>{data.districts.find(item => item.code === pair.district_code)?.name} · {data.indicators.find(item => item.id === pair.indicator)?.name || pair.indicator}</span><b>{fmt(pair.value)}</b></div>)}</div> : <p className="no-critical">Критических показателей нет.</p> }

function DistrictMap({ districts, selected, onSelect, note, values }: { districts: District[]; selected: string; onSelect: (code: string) => void; note: string; values?: Quarter }) {
  const bounds = useMemo(() => ({ minLat: Math.min(...districts.map(item => item.map_anchor.latitude)), maxLat: Math.max(...districts.map(item => item.map_anchor.latitude)), minLon: Math.min(...districts.map(item => item.map_anchor.longitude)), maxLon: Math.max(...districts.map(item => item.map_anchor.longitude)) }), [districts])
  return <div className="schematic-map" title={note}><div className="map-road road-one"/><div className="map-road road-two"/><div className="map-road road-three"/><div className="map-river"/><div className="map-caption">АСТАНА · УСЛОВНАЯ СХЕМА</div>{districts.map(district => { const x = 12 + 76 * (district.map_anchor.longitude - bounds.minLon) / (bounds.maxLon - bounds.minLon || 1); const y = 16 + 68 * (bounds.maxLat - district.map_anchor.latitude) / (bounds.maxLat - bounds.minLat || 1); const score = values?.districts.find(item => item.district_code === district.code)?.score; return <button key={district.code} className={`map-marker ${selected === district.code ? 'active' : ''}`} style={{ left: `${x}%`, top: `${y}%` }} onClick={() => onSelect(district.code)}><strong>{district.name}</strong>{score !== undefined && <span>{fmt(score, 2)}</span>}</button> })}</div>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
