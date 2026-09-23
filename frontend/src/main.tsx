import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { explain, getData, simulate } from './api'
import { ResultEvidence } from './ResultEvidence'
import { ScenarioComparison } from './ScenarioComparison'
import { ExperienceLayer } from './ExperienceLayer'
import { forDataset, loadComparison, saveComparison } from './comparison'
import type { ComparisonSlots, Slot } from './comparison'
import type { Advisor, CriticalPair, DataSet, Decision, District, Measure, Quarter, SimulationSuccess } from './types'
import './styles.css'

type Page = 'welcome' | 'center' | 'decisions' | 'result' | 'map' | 'compare'
const fmt = (value: number, digits = 1) => value.toLocaleString('ru-RU', { minimumFractionDigits: digits, maximumFractionDigits: digits })
const signed = (value: number, digits = 1) => `${value > 0 ? '+' : ''}${fmt(value, digits)}`

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
  const [comparison, setComparison] = useState<ComparisonSlots>(loadComparison)
  const scenarioRevision = useRef(0)

  useEffect(() => { saveComparison(comparison) }, [comparison])
  useEffect(() => { window.scrollTo(0, 0) }, [page])

  const reload = async () => {
    setLoading(true); setLoadError(''); setBaseline(null)
    try {
      const loaded = await getData()
      setData(loaded)
      setComparison(current => forDataset(current, loaded.dataset_hash))
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
  const comparisonA = data && comparison.A?.dataset_hash === data.dataset_hash ? comparison.A : null
  const comparisonB = data && comparison.B?.dataset_hash === data.dataset_hash ? comparison.B : null

  const choose = (measure: Measure) => {
    if (!data) return
    const existing = choices.find(choice => choice.measure_id === measure.id)
    if (existing) {
      scenarioRevision.current += 1
      setChoices(choices.filter(choice => choice.measure_id !== measure.id))
      setResult(null); setAdvisor(null); setAdvisorError(''); setAdvisorLoading(false)
      setViolations([]); setRunError('')
      return
    }
    const next: Decision = { measure_id: measure.id, ...(measure.scope === 'district' ? { district_code: districtCode } : {}) }
    if (choices.length >= data.decisions_required || localIssues(data, [...choices, next]).length) return
    scenarioRevision.current += 1
    setChoices([...choices, next]); setViolations([]); setRunError('')
    setResult(null); setAdvisor(null); setAdvisorError(''); setAdvisorLoading(false)
  }
  const changeDistrict = (measureId: string, code: string) => {
    if (!data) return
    const next = choices.map(choice => choice.measure_id === measureId ? { ...choice, district_code: code } : choice)
    scenarioRevision.current += 1
    setChoices(next); setViolations([])
    setResult(null); setAdvisor(null); setAdvisorError(''); setAdvisorLoading(false)
  }
  const run = async () => {
    if (!canRun) return
    const revision = ++scenarioRevision.current
    setRunning(true); setRunError(''); setViolations([]); setAdvisor(null); setAdvisorError('')
    try {
      const response = await simulate(choices)
      if (revision !== scenarioRevision.current) return
      if (!response.valid) { setViolations(response.violations.map(item => item.message)); return }
      setResult(response); setQuarterIndex(response.quarters.at(-1)?.quarter ?? 8); setPage('result')
      setAdvisorLoading(true)
      try {
        const explanation = await explain(response)
        if (revision === scenarioRevision.current) setAdvisor(explanation)
      }
      catch (error) {
        if (revision === scenarioRevision.current) setAdvisorError(error instanceof Error ? error.message : 'Не удалось загрузить объяснение')
      }
      finally { setAdvisorLoading(false) }
    } catch (error) {
      if (revision === scenarioRevision.current) setRunError(error instanceof Error ? error.message : 'Ошибка расчёта')
    }
    finally { setRunning(false) }
  }
  const reset = () => { scenarioRevision.current += 1; setChoices([]); setResult(null); setAdvisor(null); setAdvisorError(''); setAdvisorLoading(false); setViolations([]); setRunError(''); setPage('center') }
  const saveResult = (slot: Slot) => {
    if (!result || !data || result.dataset_hash !== data.dataset_hash) return
    setComparison(current => ({ ...forDataset(current, data.dataset_hash), [slot]: result }))
    setPage('compare')
  }
  const editSaved = (slot: Slot) => {
    const saved = slot === 'A' ? comparisonA : comparisonB
    if (!saved) return
    scenarioRevision.current += 1
    setChoices(saved.decisions)
    setResult(null); setAdvisor(null); setAdvisorError(''); setAdvisorLoading(false)
    setViolations([]); setRunError('')
    setPage('decisions')
  }

  if (loading) return <div className="fullscreen-state"><span className="brand-mark">A<span>•</span></span><div className="spinner"/><h1>Загружаем ситуационный центр</h1><p>Получаем районы, показатели и меры из API</p></div>
  if (!data) return <div className="fullscreen-state"><span className="brand-mark">A<span>•</span></span><h1>Данные города недоступны</h1><p>{loadError}</p><button className="primary" onClick={() => void reload()}>Повторить загрузку →</button></div>
  if (!data.districts.length || !data.indicators.length || !data.measures.length) return <div className="fullscreen-state"><span className="brand-mark">A<span>•</span></span><h1>Пока нет данных для сценария</h1><p>API вернул пустой список районов, показателей или мер.</p><button className="primary" onClick={() => void reload()}>Проверить снова →</button></div>

  return <div className="app-shell" data-page={page}>
    <header className="topbar"><button className="brand" onClick={() => setPage('welcome')}><span className="brand-mark">A<span>•</span></span><span>AKIM AI<small>СИТУАЦИОННЫЙ ЦЕНТР</small></span></button><div className="topnav"><span>СИМУЛЯТОР ГОРОДА</span><span> / </span><strong>{page === 'welcome' ? 'Старт' : page === 'center' ? 'Обзор города' : page === 'decisions' ? 'Пять решений' : page === 'compare' ? 'Сравнение A/B' : 'Результат'}</strong></div><div className="topright"><span className="live-dot"/> Dataset {data.version}<span className="top-divider"/> Бюджет {data.budget} ед.{(comparisonA || comparisonB) && <button className="compare-nav" onClick={() => setPage('compare')}>Сравнение A/B</button>}</div></header>
    <main>
      {page === 'welcome' && <section className="welcome content-width"><div className="eyebrow">ГЛАВНЫЙ ЭКРАН / 01</div><div className="welcome-grid"><div><h1>Вы — аким.<br/>У вас {data.budget} единиц<br/>и {data.decisions_required} решений.</h1><p>Распределите ограниченный бюджет между районами. Посмотрите последствия для города через {data.horizon_quarters} кварталов и разберитесь, почему меняется оценка.</p><button className="primary" onClick={() => setPage('center')}>Начать игру <span>↗</span></button><div className="micro">1 ход · {data.decisions_required} мер · {data.horizon_quarters} кварталов последствий</div></div><div className="welcome-card"><div className="eyebrow">СИТУАЦИЯ СЕЙЧАС</div><h2>Пять районов. Один бюджет.</h2><DistrictMap districts={data.districts} indicators={data.indicators} selected={districtCode} onSelect={setDistrictCode} note={data.map_anchor_note}/><div className="welcome-stat"><span>БАЗОВЫЙ SCORE</span><strong>{baseline === null ? '—' : fmt(baseline, 2)}</strong><small>{baseline === null ? 'Ожидаем расчёт backend' : 'Из ответа Simulation Engine'}</small></div></div></div><div className="steps"><span>01&nbsp; Изучите районы</span><span>02&nbsp; Примите {data.decisions_required} решений</span><span>03&nbsp; Разберите эффект</span></div></section>}
      {page === 'center' && <section className="dashboard content-width"><div className="section-heading"><div><div className="eyebrow">РАЙОНЫ ГОРОДА / 02</div><h1>Астана. Пять районов сценария.</h1><p>Выберите район на схеме, затем изучите показатели и проблемные места.</p></div><button className="primary" onClick={() => setPage('decisions')}>Создать сценарий ↗</button></div><div className="center-grid"><aside className="district-list"><div className="panel-title">РАЙОНЫ ГОРОДА</div>{data.districts.map(district => <button className={`district-item ${districtCode === district.code ? 'active' : ''}`} key={district.code} onClick={() => setDistrictCode(district.code)}><span><strong>{district.name}</strong><small>{district.profile}</small></span><b>{district.indicators ? Math.min(...Object.values(district.indicators)) : '—'}</b></button>)}<div className="mini-metrics"><div><span>БАЗОВЫЙ SCORE</span><strong>{baseline === null ? '—' : fmt(baseline, 2)}</strong></div><div><span>БЮДЖЕТ</span><strong>{data.budget}</strong></div><div><span>РЕШЕНИЯ</span><strong>{choices.length}/{data.decisions_required}</strong></div></div></aside><div className="map-panel"><div className="panel-title">КАРТА И ИНДЕКС НАСТРОЕНИЯ <span>Данные модели · выберите район</span></div><DistrictMap districts={data.districts} indicators={data.indicators} selected={districtCode} onSelect={setDistrictCode} note={data.map_anchor_note}/><div className="map-foot"><span>● Точки привязаны к координатам из API, контур схематичный</span><span>Настроение рассчитано по синтетическим показателям, не является опросом жителей</span></div></div><aside className="insight-panel"><div className="panel-title">В ФОКУСЕ / {selectedDistrict?.name.toUpperCase()}</div><h2>{selectedDistrict?.profile}</h2><div className="insight-box"><span>КРИТИЧЕСКИЕ ПОКАЗАТЕЛИ</span>{critical?.length ? critical.map(item => <div className="critical-row" key={item.id}><span>{item.name}</span><b>{selectedDistrict?.indicators[item.id]}/100</b></div>) : <p>Показателей ниже {data.critical_threshold} нет.</p>}</div><div className="insight-box soft"><span>НИЗКИЕ ПОКАЗАТЕЛИ</span>{weakest.map(item => <div className="critical-row" key={item.id}><span>{item.name}</span><b>{selectedDistrict?.indicators[item.id]}</b></div>)}</div><button className="secondary full" onClick={() => setPage('decisions')}>Подобрать меры для города →</button></aside></div><div className="indicator-grid">{data.indicators.map(indicator => <div className="indicator-tile" key={indicator.id}><span>{indicator.id} · {indicator.direction}</span><strong>{selectedDistrict?.indicators[indicator.id]}</strong><div className="bar"><i style={{ width: `${selectedDistrict?.indicators[indicator.id] || 0}%` }}/></div><small>{indicator.name}</small></div>)}</div></section>}
      {page === 'decisions' && <section className="decisions-layout content-width"><aside className="selection-rail"><div className="eyebrow">ВАШ ПЛАН</div><h2>{choices.length} {choices.length === 1 ? 'решение' : 'решений'}</h2><p>из {data.decisions_required} необходимых</p><div className="budget-number">{spent} <span>/ {data.budget}</span></div><div className="bar budget-bar"><i style={{ width: `${Math.min(100, spent / data.budget * 100)}%` }}/></div><small>Использовано {spent} ед. · осталось {data.budget - spent} ед.</small><div className="selected-list">{choices.length ? choices.map((choice, index) => { const measure = data.measures.find(item => item.id === choice.measure_id)!; return <div className="selected-card" key={choice.measure_id}><div><b>{String(index + 1).padStart(2, '0')}</b><strong>{measure.name}</strong><button aria-label={`Убрать ${measure.name}`} onClick={() => choose(measure)}>×</button></div><small>{measure.id} · {measure.cost} ед. · {measure.scope === 'city' ? 'весь город' : data.districts.find(item => item.code === choice.district_code)?.name}</small>{measure.scope === 'district' && <select aria-label={`Район для ${measure.name}`} value={choice.district_code} onChange={event => changeDistrict(measure.id, event.target.value)}>{data.districts.map(district => <option value={district.code} key={district.code}>{district.name}</option>)}</select>}</div> }) : <div className="empty-selection">Выберите меры в каталоге справа.</div>}</div><button className="text-button" onClick={() => setPage('center')}>← К обзору города</button></aside><div className="catalog"><div className="eyebrow">СЦЕНАРИЙ / ВЫБОР РЕШЕНИЙ</div><h1>Что вы измените за {data.horizon_quarters} кварталов?</h1><p>Выбирайте меры для районов или всего города. Ограничения проверит backend.</p><div className="catalog-toolbar"><label>Район для мер <select value={districtCode} onChange={event => setDistrictCode(event.target.value)}>{data.districts.map(district => <option value={district.code} key={district.code}>{district.name}</option>)}</select></label><div className="filters">{['Все', ...data.directions].map(direction => <button className={filter === direction ? 'active' : ''} onClick={() => setFilter(direction)} key={direction}>{direction}</button>)}</div></div><div className="measure-list">{data.measures.filter(measure => filter === 'Все' || filter === measure.direction).map(measure => { const selected = choices.some(choice => choice.measure_id === measure.id); const next = [...choices, { measure_id: measure.id, ...(measure.scope === 'district' ? { district_code: districtCode } : {}) }]; const blocked = !selected && (choices.length >= data.decisions_required || localIssues(data, next).length > 0); return <div className={`measure-card ${selected ? 'selected' : ''}`} key={measure.id}><div className="measure-top"><span className="measure-id">{measure.id}</span><span>{measure.direction}</span><span>{measure.scope === 'city' ? 'Весь город' : selected ? data.districts.find(item => item.code === choices.find(choice => choice.measure_id === measure.id)?.district_code)?.name : selectedDistrict?.name}</span></div><h3>{measure.name}</h3><div className="effect-tags">{Object.entries(measure.effects).map(([id, value]) => <span key={id}>{data.indicators.find(item => item.id === id)?.name || id} <b>{value > 0 ? '+' : ''}{value}</b></span>)}</div><div className="measure-bottom"><span>{measure.cost} ед. <em>· лаг {measure.lag} кв.</em></span><button className={selected ? 'remove-choice' : 'add-choice'} disabled={blocked} onClick={() => choose(measure)}>{selected ? 'Убрать' : blocked ? 'Недоступно' : 'Добавить +'}</button></div></div> })}</div></div><aside className="guidance"><div className="eyebrow">ПОМОЩЬ С РЕШЕНИЕМ</div><h2>Сначала причина, потом действие.</h2><p>У Нуры и других районов разные проблемные места. Сравните исходные показатели перед выбором.</p><div className="guidance-box"><b>ОГРАНИЧЕНИЯ</b><ul><li>Ровно {data.decisions_required} решений</li><li>Бюджет не выше {data.budget}</li><li>Не более {data.max_per_direction} мер в одном направлении</li><li>Несовместимые меры нельзя объединять</li></ul></div>{issues.map(issue => <p className="inline-error" key={issue}>{issue}</p>)}{violations.map(issue => <p className="inline-error" key={issue}>{issue}</p>)}{runError && <p className="inline-error" role="alert">{runError}</p>}<button className="primary full" disabled={!canRun} onClick={() => void run()}>{running ? 'Рассчитываем…' : 'SIMULATE →'}</button><small>Итоговый Score рассчитывает только backend.</small></aside><div className="mobile-run"><span>{choices.length}/{data.decisions_required} мер · {spent}/{data.budget} ед.</span><button className="primary" disabled={!canRun} onClick={() => void run()}>{running ? 'Расчёт…' : 'SIMULATE →'}</button></div></section>}
      {result && page === 'result' && <section className="result-page content-width"><div className="eyebrow">РЕЗУЛЬТАТ СИМУЛЯЦИИ / 04</div><div className="section-heading"><div><h1>Как {result.decisions.length} мер меняют город</h1><p>{result.dataset_version} · расчёт Simulation Engine · горизонт Q0–Q{data.horizon_quarters}</p></div><button className="secondary" onClick={reset}>Новый сценарий ↗</button></div><div className="compare-actions"><span>Сохраните два расчёта и сравните последствия.</span><button className="secondary" onClick={() => saveResult('A')}>Сохранить в A</button><button className="secondary" onClick={() => saveResult('B')}>Сохранить в B</button>{(comparisonA || comparisonB) && <button className="text-button" onClick={() => setPage('compare')}>Сравнить A/B →</button>}</div><div className="result-grid"><div><div className="score-panel"><div className="eyebrow">ИНДЕКС ГОРОДА</div><div className="score-row"><div><strong>{fmt(result.baseline_score, 2)}</strong><span>ДО РЕШЕНИЙ</span></div><b>→</b><div><strong>{fmt(result.score, 2)}</strong><span>ПОСЛЕ РЕШЕНИЙ</span></div><div className="score-delta">{signed(result.score_delta, 2)}<small>к базовому Score</small></div></div><p>Средний показатель города: {fmt(result.city_average_before, 2)} → {fmt(result.city_average_after, 2)}. Потрачено {result.spent} из {result.budget} ед.</p></div><div className="block-heading"><h2>Районы · до и после</h2><button className="text-button" onClick={() => setPage('map')}>Посмотреть на карте →</button></div>{result.districts.length ? <div className="district-results">{result.districts.map(district => <button key={district.code} onClick={() => { setDistrictCode(district.code); setPage('map') }}><span>{district.name}</span><strong>{fmt(district.before.score, 2)} → {fmt(district.after.score, 2)}</strong><em>{signed(district.after.score - district.before.score)}</em></button>)}</div> : <div className="empty-selection">Backend не вернул результаты по районам.</div>}<div className="two-columns"><div className="card"><div className="panel-title">КРИТИЧЕСКИЕ ПОКАЗАТЕЛИ</div><p>До: {result.critical_pairs_before.length} · После: {result.critical_pairs_after.length}</p><CriticalList pairs={result.critical_pairs_after} data={data}/></div><div className="card"><div className="panel-title">ВАШИ РЕШЕНИЯ</div>{result.decisions.map(choice => { const measure = data.measures.find(item => item.id === choice.measure_id); return <div className="choice-summary" key={choice.measure_id}><b>{choice.measure_id}</b><span>{measure?.name}</span><small>{choice.district_code ? data.districts.find(item => item.code === choice.district_code)?.name : 'Весь город'}</small></div> })}</div></div></div><aside className="advisor-panel"><div className="eyebrow">AI ADVISOR</div><h2>Где выигрыш,<br/>а где риск?</h2>{advisorLoading && <p>Готовим объяснение…</p>}{advisor?.status === 'available' && <div className="advisor-copy"><div><b>Сильные стороны</b><p>{advisor.strengths}</p></div><div><b>Слабые стороны</b><p>{advisor.weaknesses}</p></div><div><b>Компромиссы</b><p>{advisor.tradeoffs}</p></div><div><b>Оставшиеся критические показатели</b><p>{advisor.remaining_critical_indicators}</p></div></div>}{advisor?.status === 'unavailable' && <div className="advisor-unavailable"><b>AI Advisor недоступен</b><p>{advisor.reason}</p><small>Числовой результат и поквартальная динамика доступны.</small></div>}{advisorError && <div className="advisor-unavailable" role="alert"><b>Не удалось получить объяснение</b><p>{advisorError}</p><small>Расчёт остаётся доступен.</small></div>}<button className="primary full" onClick={() => setPage('map')}>Посмотреть динамику →</button></aside></div><ResultEvidence data={data} result={result} onEdit={() => setPage('decisions')}/></section>}
      {page === 'compare' && <ScenarioComparison data={data} a={comparisonA} b={comparisonB} backLabel={result ? 'К результату' : 'К обзору города'} onBack={() => setPage(result ? 'result' : 'center')} onNew={reset} onEdit={editSaved}/>}
      {result && page === 'map' && <section className="map-result content-width"><div className="section-heading"><div><div className="eyebrow">ПОСЛЕДСТВИЯ / Q{quarter?.quarter ?? quarterIndex}</div><h1>Карта последствий: что изменилось?</h1><p>Нажмите на район и квартал, чтобы сравнить значения.</p></div><button className="secondary" onClick={() => setPage('result')}>← К результату</button></div><div className="center-grid"><aside className="district-list"><div className="panel-title">РАЙОНЫ · ДО / Q{quarter?.quarter}</div>{result.districts.map(district => { const current = quarter?.districts.find(item => item.district_code === district.code); return <button className={`district-item ${districtCode === district.code ? 'active' : ''}`} key={district.code} onClick={() => setDistrictCode(district.code)}><span><strong>{district.name}</strong><small>{fmt(district.before.score, 2)} → {current ? fmt(current.score, 2) : '—'}</small></span><b>{current ? signed(current.score - district.before.score) : '—'}</b></button> })}<div className="mini-metrics"><div><span>ИНДЕКС ГОРОДА</span><strong>{fmt(result.baseline_score, 2)} → {quarter ? fmt(quarter.score, 2) : '—'}</strong></div></div></aside><div className="map-panel"><div className="panel-title">КАРТА НАСТРОЕНИЯ · Q{quarter?.quarter ?? '—'} <span>по модели решений</span></div><DistrictMap districts={data.districts} indicators={data.indicators} selected={districtCode} onSelect={setDistrictCode} note={data.map_anchor_note} values={quarter}/><div className="timeline"><div className="panel-title">ДИНАМИКА ПО КВАРТАЛАМ</div><div className="quarter-buttons">{result.quarters.length ? result.quarters.map(item => <button className={quarterIndex === item.quarter ? 'active' : ''} onClick={() => setQuarterIndex(item.quarter)} key={item.quarter}>Q{item.quarter}<span>{fmt(item.score, 2)}</span></button>) : <p>Поквартальные данные не вернулись.</p>}</div></div></div><aside className="insight-panel"><div className="panel-title">ДЕТАЛИ / {selectedDistrict?.name.toUpperCase()}</div><h2>Показатели района</h2>{data.indicators.map(indicator => { const before = result.districts.find(item => item.code === districtCode)?.before.indicators[indicator.id]; const after = quarter?.districts.find(item => item.district_code === districtCode)?.indicators[indicator.id]; return <div className="indicator-comparison" key={indicator.id}><span>{indicator.name}</span><b>{before === undefined ? '—' : fmt(before)} → {after === undefined ? '—' : fmt(after)}</b><em>{before === undefined || after === undefined ? '—' : signed(after - before)}</em></div> })}<div className="insight-box soft"><span>КРИТИЧЕСКИЕ В Q{quarter?.quarter}</span><CriticalList pairs={quarter?.critical_pairs.filter(item => item.district_code === districtCode) || []} data={data}/></div></aside></div></section>}
    </main><ExperienceLayer page={page} chosen={choices.length} required={data.decisions_required}/><footer><span>AKIM AI · CITY DECISION SIMULATOR</span><span>Синтетические данные · не прогноз реальных городских последствий</span></footer>
  </div>
}

function CriticalList({ pairs, data }: { pairs: CriticalPair[]; data: DataSet }) { return pairs.length ? <div className="critical-list">{pairs.map(pair => <div className="critical-row" key={`${pair.district_code}-${pair.indicator}`}><span>{data.districts.find(item => item.code === pair.district_code)?.name} · {data.indicators.find(item => item.id === pair.indicator)?.name || pair.indicator}</span><b>{fmt(pair.value)}</b></div>)}</div> : <p className="no-critical">Критических показателей нет.</p> }

function DistrictMap({ districts, indicators, selected, onSelect, note, values }: { districts: District[]; indicators: DataSet['indicators']; selected: string; onSelect: (code: string) => void; note: string; values?: Quarter }) {
  const mapRef = useRef<HTMLDivElement>(null)
  const bounds = useMemo(() => ({ minLat: Math.min(...districts.map(item => item.map_anchor.latitude)), maxLat: Math.max(...districts.map(item => item.map_anchor.latitude)), minLon: Math.min(...districts.map(item => item.map_anchor.longitude)), maxLon: Math.max(...districts.map(item => item.map_anchor.longitude)) }), [districts])
  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== 'mouse' || !mapRef.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const rect = mapRef.current.getBoundingClientRect()
    mapRef.current.style.setProperty('--pointer-x', `${event.clientX - rect.left}px`)
    mapRef.current.style.setProperty('--pointer-y', `${event.clientY - rect.top}px`)
    mapRef.current.style.setProperty('--tilt-x', `${((event.clientY - rect.top) / rect.height - .5) * -7}px`)
    mapRef.current.style.setProperty('--tilt-y', `${((event.clientX - rect.left) / rect.width - .5) * 7}px`)
  }
  const resetPointer = () => {
    if (!mapRef.current) return
    mapRef.current.style.setProperty('--pointer-x', '50%')
    mapRef.current.style.setProperty('--pointer-y', '50%')
    mapRef.current.style.setProperty('--tilt-x', '0px')
    mapRef.current.style.setProperty('--tilt-y', '0px')
  }
  const moodAt = (score: number) => score >= 68 ? { label: 'хорошо', mood: 'happy' } : score >= 50 ? { label: 'ровно', mood: 'calm' } : { label: 'нужна забота', mood: 'sad' }
  const scores = districts.map(district => {
    const quarterScore = values?.districts.find(item => item.district_code === district.code)?.score
    const score = quarterScore ?? indicators.reduce((sum, indicator) => sum + indicator.weight * (district.indicators[indicator.id] ?? 0), 0)
    return { district, score }
  })
  const cityScore = scores.length ? scores.reduce((sum, item) => sum + item.score * item.district.population_share, 0) / scores.reduce((sum, item) => sum + item.district.population_share, 0) : 0
  return <div ref={mapRef} className="schematic-map astana-map" title={note} onPointerMove={onPointerMove} onPointerLeave={resetPointer}>
    <div className="map-glow" aria-hidden="true"/>
    <svg className="map-art" viewBox="0 0 1000 650" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs><linearGradient id="city-paper" x1="0" x2="1" y1="0" y2="1"><stop stopColor="#f8f5e9"/><stop offset="1" stopColor="#e8f1df"/></linearGradient><linearGradient id="esil-water" x1="0" x2="1"><stop stopColor="#a8d9da"/><stop offset=".5" stopColor="#bce5df"/><stop offset="1" stopColor="#92cfd4"/></linearGradient><pattern id="city-blocks" width="74" height="62" patternUnits="userSpaceOnUse" patternTransform="rotate(-13)"><rect x="5" y="6" width="26" height="18" rx="4" fill="#fffdf6" stroke="#e2dfcd"/><rect x="38" y="8" width="29" height="15" rx="4" fill="#f5f0df" stroke="#e2dfcd"/><rect x="15" y="34" width="43" height="19" rx="5" fill="#fffdf6" stroke="#e2dfcd"/></pattern><filter id="map-soft-shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="8" stdDeviation="10" floodColor="#386351" floodOpacity=".12"/></filter></defs>
      <rect width="1000" height="650" fill="url(#city-paper)"/><path d="M0 0h1000v150c-102 47-159 26-247 73-92 49-170 59-267 34-90-23-184 12-267 63C132 371 61 377 0 363Z" fill="#dcebd0"/><path d="M0 400c115-44 183-36 289-75 93-34 162-42 248-11 97 35 143 27 227-17 85-45 160-59 236-37v390H0Z" fill="#d7e9cd"/>
      <path d="M-65 260c154 13 208 74 341 80 143 7 207-87 350-82 137 5 201 92 420 71" fill="none" stroke="#8bcacb" strokeWidth="104" strokeLinecap="round"/><path d="M-65 260c154 13 208 74 341 80 143 7 207-87 350-82 137 5 201 92 420 71" fill="none" stroke="url(#esil-water)" strokeWidth="86" strokeLinecap="round"/><path d="M-65 260c154 13 208 74 341 80 143 7 207-87 350-82 137 5 201 92 420 71" fill="none" stroke="#eff9eb" strokeWidth="2" strokeDasharray="3 13" opacity=".85"/>
      <path d="M-30 155 103 189 252 181 384 229 497 210 609 235 724 204 879 235 1030 199M-25 454l136-35 130 27 126-31 131 34 126-31 144 36 148-21M61-20l40 124-23 104 28 108-18 119 32 119M278-12l-19 115 32 99-15 116 30 109-24 136M510-30l21 126-30 110 25 121-20 114 28 155M743-20l-18 113 29 120-25 111 30 103-19 147M937-23l-20 133 23 113-31 124 27 122" fill="none" stroke="#fffdf5" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round"/><path d="M-30 155 103 189 252 181 384 229 497 210 609 235 724 204 879 235 1030 199M-25 454l136-35 130 27 126-31 131 34 126-31 144 36 148-21M61-20l40 124-23 104 28 108-18 119 32 119M278-12l-19 115 32 99-15 116 30 109-24 136M510-30l21 126-30 110 25 121-20 114 28 155M743-20l-18 113 29 120-25 111 30 103-19 147M937-23l-20 133 23 113-31 124 27 122" fill="none" stroke="#d8d9c8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M0 115c109 31 153 5 230 12 87 8 142 41 201 75M789 0c-10 64-2 101 54 144 46 35 74 87 86 148M0 537c135-42 210-11 303 28M562 650c9-67 50-104 118-127 82-27 168-24 320 5" fill="none" stroke="#f3b86e" strokeWidth="5" strokeLinecap="round" strokeDasharray="13 9" opacity=".75"/>
      <path d="M118 92c30-31 73-36 111-11l-14 44-69 13-43-18zM809 387c39-35 103-29 132 7l-12 45-78 15-50-25zM374 512c34-31 85-25 113 9l-15 36-74 9-38-24z" fill="#b9d7a5" stroke="#a3c596" strokeWidth="3"/><g fill="#fff4d4" opacity=".85"><circle cx="155" cy="105" r="4"/><circle cx="175" cy="96" r="5"/><circle cx="205" cy="119" r="4"/><circle cx="849" cy="409" r="4"/><circle cx="877" cy="422" r="5"/><circle cx="411" cy="532" r="4"/><circle cx="445" cy="542" r="5"/></g>
      <g fill="#8daaa0" fontFamily="Arial,sans-serif" fontSize="15" fontWeight="700" letterSpacing="3"><text x="445" y="319">ЕСИЛЬ</text><text x="468" y="417">РАЙОНЫ АСТАНЫ</text></g><g fill="#6dabb0" fontFamily="Arial,sans-serif" fontSize="13" fontWeight="700" letterSpacing="2"><text x="383" y="301">РЕКА ЕСИЛЬ</text></g>
      <g transform="translate(902 76)" opacity=".66"><path d="M0 32 13 0l13 32-13-8z" fill="#fff" stroke="#7d998a" strokeWidth="2"/><text x="9" y="53" fill="#638072" fontSize="12" fontWeight="700">N</text></g>
      <g transform="translate(54 580)" fill="none" stroke="#698977" strokeWidth="3" opacity=".48"><path d="M0 0h95M0 8h95M0 16h95M0 24h95"/><path d="M0-4v32M32-4v32M64-4v32M95-4v32"/></g>
    </svg>
    <div className="map-topline"><span className="map-kicker"><i/> ASTANA · LIVE MODEL</span><span className="map-compass">N&nbsp; ↑</span></div>
    <div className="map-city-score"><span>ИНДЕКС БЛАГОПОЛУЧИЯ</span><strong>{fmt(cityScore, 1)}<small>/100</small></strong><i>{moodAt(cityScore).label}</i></div>
    {scores.map(({ district, score }, index) => {
      const x = 11 + 78 * (district.map_anchor.longitude - bounds.minLon) / (bounds.maxLon - bounds.minLon || 1)
      const y = 18 + 60 * (bounds.maxLat - district.map_anchor.latitude) / (bounds.maxLat - bounds.minLat || 1)
      const mood = moodAt(score)
      return <button key={district.code} aria-label={`${district.name}: индекс ${fmt(score, 1)} из 100, состояние ${mood.label}`} className={`map-marker astana-marker ${mood.mood} ${selected === district.code ? 'active' : ''}`} style={{ left: `${x}%`, top: `${y}%`, animationDelay: `${index * -0.45}s` }} onClick={() => onSelect(district.code)}><span className="mood-face" aria-hidden="true"/><span className="marker-copy"><strong>{district.name}</strong><small>{fmt(score, 1)} · {mood.label}</small></span><span className="marker-pulse" aria-hidden="true"/></button>
    })}
    <div className="map-legend"><span><i className="happy-dot"/> 68+ хорошо</span><span><i className="calm-dot"/> 50–67 ровно</span><span><i className="sad-dot"/> &lt;50 нужна забота</span></div>
  </div>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
