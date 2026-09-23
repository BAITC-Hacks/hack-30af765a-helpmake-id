import { useEffect, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { getSimulationData, postSimulation } from './api/client'
import {
  adaptSimulationData, adaptSimulationResult, areaLabels, REQUIRED_DECISIONS,
  type Area, type Decision, type District, type IndicatorData, type Initiative, type ModelData, type SimulationResult,
} from './data/model'

const areaIcons: Record<Area, string> = {
  transport: '↗', environment: '✳', social: '✚', safety: '◇', services: '⌘',
}

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function CityMap({ districts, selectedId, onSelect }: { districts: District[]; selectedId: string; onSelect: (id: string) => void }) {
  const [element, setElement] = useState<HTMLDivElement | null>(null)
  const [map, setMap] = useState<L.Map | null>(null)

  useEffect(() => {
    if (!element) return
    const instance = L.map(element, { zoomControl: false, scrollWheelZoom: false }).setView([51.15, 71.44], 11)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 18,
    }).addTo(instance)
    L.control.zoom({ position: 'bottomright' }).addTo(instance)
    setMap(instance)
    return () => { instance.remove(); setMap(null) }
  }, [element])

  useEffect(() => {
    if (!map) return
    const markers = districts.map((district) => {
      const icon = L.divIcon({
        className: `map-pin ${selectedId === district.id ? 'is-active' : ''}`,
        html: `<span class="map-pin-name">${district.name}</span><strong>${district.score.toFixed(1)}</strong>`,
        iconSize: [92, 47], iconAnchor: [46, 24],
      })
      return L.marker(district.location, { icon }).on('click', () => onSelect(district.id)).addTo(map)
    })
    const selected = districts.find((district) => district.id === selectedId)
    if (selected) map.flyTo(selected.location, Math.max(map.getZoom(), 11), { duration: 0.45 })
    return () => markers.forEach((marker) => marker.remove())
  }, [map, districts, selectedId, onSelect])

  return <div ref={setElement} className="city-map" role="application" aria-label="Карта Астаны с условными точками пяти районов" />
}

function IndicatorOverview({ district, districts, indicators, onSelect }: {
  district: District
  districts: District[]
  indicators: IndicatorData[]
  onSelect: (id: string) => void
}) {
  const concerns = districts.flatMap((item) => indicators.map((indicator) => ({
    district: item.name,
    districtId: item.id,
    name: indicator.name,
    value: item.indicators[indicator.id],
  }))).filter((item) => item.value < 50).sort((a, b) => a.value - b.value).slice(0, 5)

  return <div className="indicator-overview">
    <div className="indicator-overview-head"><div><span className="eyebrow">10 ПОКАЗАТЕЛЕЙ</span><h3>Профиль района «{district.name}»</h3></div><span>Шкала 0–100 · критично ниже 40</span></div>
    <div className="indicator-overview-layout">
      <div className="indicator-list">{indicators.map((indicator) => {
        const value = district.indicators[indicator.id]
        return <div className={`indicator-row ${value < 40 ? 'is-critical' : value < 50 ? 'needs-attention' : ''}`} key={indicator.id}>
          <div className="indicator-row-head"><span><b>{indicator.id}</b> {indicator.name}</span><strong>{value.toFixed(0)}</strong></div>
          <div className="indicator-track"><span style={{ width: `${value}%` }}/></div>
          {value < 40 && <small>Критический показатель</small>}
        </div>
      })}</div>
      <aside className="concern-panel"><span className="eyebrow">ПРОБЛЕМНЫЕ МЕСТА</span><h4>Где городу нужнее внимание</h4><p>Пять самых низких значений среди всех районов и показателей.</p><div className="concern-list">{concerns.map((item) => <button key={`${item.districtId}-${item.name}`} onClick={() => onSelect(item.districtId)}><span><strong>{item.district}</strong><small>{item.name}</small></span><b className={item.value < 40 ? 'critical' : ''}>{item.value}</b></button>)}</div><small className="concern-note">Красным отмечены значения строго ниже 40.</small></aside>
    </div>
  </div>
}

function IndicatorComparison({ result, indicators, selectedId, onSelect }: {
  result: SimulationResult
  indicators: IndicatorData[]
  selectedId: string
  onSelect: (id: string) => void
}) {
  const district = result.districts.find((item) => item.id === selectedId) ?? result.districts[0]
  return <div className="indicator-comparison"><div className="indicator-comparison-head"><div><span className="eyebrow">ДЕТАЛИ РЕЗУЛЬТАТА</span><h3>Показатели по районам</h3></div><span>До → после · разница</span></div><div className="comparison-tabs">{result.districts.map((item) => <button key={item.id} className={item.id === district.id ? 'selected' : ''} onClick={() => onSelect(item.id)}>{item.name}<span>{item.score.toFixed(1)} → {item.nextScore.toFixed(1)}</span></button>)}</div><div className="comparison-table" role="table" aria-label={`Показатели района ${district.name} до и после симуляции`}><div className="comparison-row comparison-labels" role="row"><span role="columnheader">Показатель</span><span role="columnheader">До</span><span role="columnheader">После</span><span role="columnheader">Изменение</span></div>{indicators.map((indicator) => {
    const before = district.beforeIndicators[indicator.id]
    const after = district.afterIndicators[indicator.id]
    const delta = after - before
    return <div className="comparison-row" role="row" key={indicator.id}><span role="cell"><b>{indicator.id}</b> {indicator.name}{after < 40 && <em>Критично</em>}</span><span role="cell">{before.toFixed(1)}</span><strong role="cell">{after.toFixed(1)}</strong><span role="cell" className={delta > 0 ? 'positive' : ''}>{delta > 0 ? '+' : ''}{delta.toFixed(1)}</span></div>
  })}</div></div>
}

function InitiativeCard({ initiative, districts, added, targetId, onTarget, onToggle, disabledReason }: {
  initiative: Initiative
  districts: District[]
  added: boolean
  targetId: string
  onTarget: (id: string) => void
  onToggle: () => void
  disabledReason: string | null
}) {
  return <article className={`initiative-card ${added ? 'is-added' : ''}`}>
    <div className="initiative-top"><span className={`area-icon ${initiative.area}`}>{areaIcons[initiative.area]}</span><span className="initiative-area">{areaLabels[initiative.area]}</span><span className="initiative-id">{initiative.id}</span><span className="initiative-cost">{initiative.cost} ед.</span></div>
    <h3>{initiative.title}</h3><span className="effect-label">Полный эффект на показатели</span><p>{initiative.description}</p>
    <div className="initiative-meta"><span>{initiative.scope === 'city' ? 'Весь город' : 'Для района'}</span><span>Лаг {initiative.lag} кв.</span></div>
    {initiative.scope === 'district' && <label className="target-label">Район применения<select value={targetId} onChange={(event) => onTarget(event.target.value)} aria-label={`Район для инициативы «${initiative.title}»`}>{districts.map((district) => <option key={district.id} value={district.id}>{district.name}</option>)}</select></label>}
    <button className={`initiative-action ${added ? 'remove' : ''}`} onClick={onToggle} disabled={!added && Boolean(disabledReason)} title={!added ? disabledReason ?? undefined : undefined}>{added ? 'Убрать из сценария' : 'Добавить решение'} <span>{added ? '×' : '+'}</span></button>
  </article>
}

export default function App() {
  const [model, setModel] = useState<ModelData | null>(null)
  const [loadError, setLoadError] = useState('')
  const [selectedDistrictId, setSelectedDistrictId] = useState('')
  const [filter, setFilter] = useState<'all' | Area>('all')
  const [targets, setTargets] = useState<Record<string, string>>({})
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [validationMessage, setValidationMessage] = useState('')
  const [simulating, setSimulating] = useState(false)

  useEffect(() => {
    getSimulationData()
      .then((raw) => {
        const next = adaptSimulationData(raw)
        setModel(next)
        setSelectedDistrictId(next.districts.find((district) => district.id === 'nura')?.id ?? next.districts[0].id)
      })
      .catch((error: unknown) => setLoadError(error instanceof Error ? error.message : 'Не удалось получить данные'))
  }, [])

  if (!model) return <div className="load-screen"><div className="load-mark">A<span>•</span></div><h1>Akim AI</h1><p>{loadError ? `Не удалось подключиться к Simulation API: ${loadError}` : 'Загружаем модель города…'}</p>{loadError && <button onClick={() => window.location.reload()}>Повторить подключение</button>}</div>

  const { districts, initiatives } = model
  const budget = model.raw.budget
  const baselineScore = model.raw.baseline_score

  const selectedDistrict = districts.find((district) => district.id === selectedDistrictId) ?? districts[0]
  const spent = decisions.reduce((total, decision) => total + (initiatives.find((item) => item.id === decision.initiativeId)?.cost ?? 0), 0)
  const remaining = budget - spent
  const visibleInitiatives = filter === 'all' ? initiatives : initiatives.filter((item) => item.area === filter)

  function incompatibilityReason(initiative: Initiative, districtId?: string): string | null {
    for (const rule of model!.raw.incompatibilities) {
      if (!rule.measures.includes(initiative.id)) continue
      const otherId = rule.measures.find((id) => id !== initiative.id)
      const other = decisions.find((decision) => decision.initiativeId === otherId)
      if (!other) continue
      if (rule.scope === 'global' || (districtId && other.districtId === districtId)) return rule.description
    }
    return null
  }

  function reasonToDisable(initiative: Initiative, districtId?: string): string | null {
    if (decisions.length >= REQUIRED_DECISIONS) return 'Уже выбрано пять решений'
    if (initiative.cost > remaining) return 'Недостаточно бюджета'
    const countInArea = decisions.filter((decision) => initiatives.find((item) => item.id === decision.initiativeId)?.area === initiative.area).length
    if (countInArea >= 2) return 'Не более двух мер в одном направлении'
    return incompatibilityReason(initiative, districtId)
  }

  function toggleDecision(initiative: Initiative) {
    setValidationMessage('')
    setResult(null)
    if (decisions.some((decision) => decision.initiativeId === initiative.id)) {
      setDecisions((current) => current.filter((decision) => decision.initiativeId !== initiative.id))
      return
    }
    const districtId = initiative.scope === 'district' ? (targets[initiative.id] ?? selectedDistrictId) : undefined
    const reason = reasonToDisable(initiative, districtId)
    if (reason) { setValidationMessage(reason); return }
    setDecisions((current) => [...current, { initiativeId: initiative.id, districtId }])
  }

  function updateTarget(initiative: Initiative, districtId: string) {
    if (decisions.some((decision) => decision.initiativeId === initiative.id)) {
      const reason = incompatibilityReason(initiative, districtId)
      if (reason) { setValidationMessage(reason); return }
    }
    setTargets((current) => ({ ...current, [initiative.id]: districtId }))
    setDecisions((current) => current.map((decision) => decision.initiativeId === initiative.id ? { ...decision, districtId } : decision))
    setResult(null)
    setValidationMessage('')
  }

  async function simulate() {
    if (decisions.length !== REQUIRED_DECISIONS) {
      setValidationMessage(`Для расчёта нужно выбрать ровно ${REQUIRED_DECISIONS} решений.`)
      return
    }
    setValidationMessage('')
    setSimulating(true)
    try {
      const response = await postSimulation(decisions)
      setResult(adaptSimulationResult(response.simulation, districts, response.explanation))
      window.requestAnimationFrame(() => scrollTo('result'))
    } catch (error) {
      setValidationMessage(error instanceof Error ? error.message : 'Расчёт не выполнен')
    } finally {
      setSimulating(false)
    }
  }

  function startAgain() {
    setDecisions([])
    setResult(null)
    setValidationMessage('')
    setFilter('all')
    scrollTo('decisions')
  }

  const highestGain = result?.districts.reduce((best, district) => district.delta > best.delta ? district : best)
  const weakestAfter = result?.districts.reduce((weakest, district) => district.nextScore < weakest.nextScore ? district : weakest)

  return <div className="site-shell">
    <aside className="sidebar">
      <a className="logo" href="#top"><span className="logo-mark">A<span>•</span></span><span>AKIM <b>AI</b><small>СИТУАЦИОННЫЙ ЦЕНТР</small></span></a>
      <div className="sidebar-section-label">РАБОЧЕЕ ПРОСТРАНСТВО</div>
      <nav aria-label="Навигация"><a href="#overview" className="nav-link active"><span>◫</span>Обзор города</a><a href="#decisions" className="nav-link"><span>▦</span>Решения <em>{decisions.length}/5</em></a><a href="#result" className="nav-link"><span>◉</span>Результат</a></nav>
      <div className="sidebar-bottom"><div className="sidebar-info-icon">i</div><strong>О концепте</strong><p>Пять решений. Один бюджет. Наглядные последствия для каждого района.</p><a href="#principles">Как это работает →</a></div>
      <div className="sidebar-foot"><span className="online-dot" /> Демо на синтетических данных</div>
    </aside>

    <main className="main-content" id="top">
      <header className="topbar"><div className="breadcrumbs">Рабочее пространство <span>/</span> <strong>Обзор города</strong></div><div className="topbar-actions"><span className="top-pill"><span className="online-dot" /> Модель сценария</span><span className="top-avatar">А</span></div></header>
      <div className="content-wrap">
        <section className="hero" id="overview"><div className="hero-copy"><div className="hero-kicker"><span /> AI SITUATION CENTER · ASTANA</div><h1>Увидеть последствия<br /><em>до принятия решения.</em></h1><p>Распределите ограниченный бюджет между районами, проверьте пять управленческих решений и узнайте, как они меняют качество жизни города.</p><div className="hero-actions"><button className="primary-button light" onClick={() => scrollTo('decisions')}>Создать сценарий <span>↗</span></button><button className="text-button" onClick={() => scrollTo('principles')}>Как работает модель <span>→</span></button></div></div><div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/><div className="hero-center"><span>ASTANA</span><b>{baselineScore.toFixed(2)}</b><small>QUALITY OF LIFE</small></div><span className="orbit-point point-one"/><span className="orbit-point point-two"/><span className="orbit-point point-three"/></div></section>

        <div className="flow-strip" aria-label="Путь сценария"><span className="flow-step current"><b>01</b> Исходное состояние</span><i>→</i><span className={decisions.length ? 'flow-step current' : 'flow-step'}><b>02</b> Пять решений</span><i>→</i><span className={result ? 'flow-step current' : 'flow-step'}><b>03</b> Последствия</span><i>→</i><span className={result ? 'flow-step current' : 'flow-step'}><b>04</b> Новый сценарий</span></div>

        <section className="summary-section"><div className="section-intro"><div><p className="eyebrow">ОБЩАЯ КАРТИНА</p><h2>Исходное состояние города</h2></div><span className="section-note">Единая отправная точка для каждого сценария</span></div><div className="metric-grid"><div className="metric-card"><div className="metric-label">ИНДЕКС КАЧЕСТВА ЖИЗНИ <span className="metric-symbol">↗</span></div><div className="metric-value">{baselineScore.toFixed(2)} <small>/ 100</small></div><p>Базовый Astana Quality of Life Score</p><div className="metric-line"><span style={{ width: `${baselineScore}%` }}/></div></div><div className="metric-card"><div className="metric-label">ОСТАТОК БЮДЖЕТА <span className="metric-symbol amber">◈</span></div><div className="metric-value">{remaining} <small>ед.</small></div><p>Из {budget} условных единиц</p><div className="metric-line gold"><span style={{ width: `${remaining}%` }}/></div></div><div className="metric-card"><div className="metric-label">РЕШЕНИЯ В СЦЕНАРИИ <span className="metric-symbol blue">✓</span></div><div className="metric-value">{decisions.length} <small>/ 5</small></div><p>Нужно ровно пять мер для расчёта</p><div className="step-dashes">{Array.from({ length: 5 }, (_, index) => <span className={index < decisions.length ? 'filled' : ''} key={index}/>)}</div></div></div></section>

        <section className="city-section"><div className="section-intro"><div><p className="eyebrow">КАРТА И ПОКАЗАТЕЛИ</p><h2>Пять районов. Разные потребности.</h2></div><span className="section-note">Выберите район на карте</span></div><div className="city-layout"><div className="map-panel"><CityMap districts={districts} selectedId={selectedDistrictId} onSelect={setSelectedDistrictId}/><div className="map-caption"><span>●</span> Точки районов показаны условно · картографическая основа OpenStreetMap</div></div><div className="district-panel"><div className="district-panel-head"><span>ВЫБРАННЫЙ РАЙОН</span><span className="outline-dot">●</span></div><h3>{selectedDistrict.name}</h3><p>{selectedDistrict.note}</p><div className="district-big-score"><strong>{selectedDistrict.score.toFixed(2)}</strong><span>БАЗОВЫЙ<br/>ИНДЕКС</span></div><div className="district-score-track"><span style={{ width: `${selectedDistrict.score}%` }}/></div><div className="district-facts"><div><span>Доля населения</span><strong>{Math.round(selectedDistrict.share * 100)}%</strong></div><div><span>Позиция среди районов</span><strong>{districts.slice().sort((a, b) => b.score - a.score).findIndex((item) => item.id === selectedDistrict.id) + 1} / 5</strong></div></div><button className="outline-button" onClick={() => scrollTo('decisions')}>Выбрать меру для района <span>→</span></button></div></div><div className="district-tabs">{districts.map((district) => <button key={district.id} className={selectedDistrictId === district.id ? 'selected' : ''} onClick={() => setSelectedDistrictId(district.id)}><span className="tab-dot"/>{district.name}<b>{district.score.toFixed(1)}</b></button>)}</div></section>

        <IndicatorOverview district={selectedDistrict} districts={districts} indicators={model.raw.indicators} onSelect={setSelectedDistrictId}/>

        <section className="decisions-section" id="decisions"><div className="section-intro"><div><p className="eyebrow">ШАГ 02 · УПРАВЛЕНЧЕСКИЙ ВЫБОР</p><h2>Соберите сценарий развития</h2><p className="section-description">Выберите ровно пять инициатив. Бюджет ограничен, а в каждом направлении доступно не более двух мер.</p></div><span className="section-counter">{decisions.length} / 5 решений</span></div><div className="scenario-layout"><div><div className="filter-row"><button className={filter === 'all' ? 'selected' : ''} onClick={() => setFilter('all')}>Все направления</button>{(Object.keys(areaLabels) as Area[]).map((area) => <button key={area} className={filter === area ? 'selected' : ''} onClick={() => setFilter(area)}>{areaLabels[area]}</button>)}</div><div className="initiative-grid">{visibleInitiatives.map((initiative) => <InitiativeCard key={initiative.id} initiative={initiative} districts={districts} added={decisions.some((decision) => decision.initiativeId === initiative.id)} targetId={targets[initiative.id] ?? decisions.find((decision) => decision.initiativeId === initiative.id)?.districtId ?? selectedDistrictId} onTarget={(id) => updateTarget(initiative, id)} onToggle={() => toggleDecision(initiative)} disabledReason={reasonToDisable(initiative, targets[initiative.id] ?? selectedDistrictId)}/>)}</div></div><aside className="scenario-panel"><div className="scenario-panel-top"><span>ВАШ СЦЕНАРИЙ</span><strong>{decisions.length}/{REQUIRED_DECISIONS}</strong></div><h3>Пять решений для города</h3><p>Результат появится после полного набора мер.</p><div className="budget-summary"><span>Бюджет использован</span><strong>{spent} / {budget}</strong></div><div className="budget-bar"><span style={{ width: `${spent}%` }}/></div><div className="selected-list">{decisions.length === 0 ? <div className="empty-decisions">Пока нет решений.<br/>Добавьте первую инициативу из каталога.</div> : decisions.map((decision, index) => { const initiative = initiatives.find((item) => item.id === decision.initiativeId)!; return <div className="selected-item" key={initiative.id}><span className="selected-number">0{index + 1}</span><div><strong>{initiative.title}</strong><small>{decision.districtId ? districts.find((district) => district.id === decision.districtId)?.name : 'Весь город'} · {initiative.cost} ед.</small></div><button onClick={() => toggleDecision(initiative)} aria-label={`Убрать «${initiative.title}»`}>×</button></div> })}</div><div className="scenario-rules"><span>✓ Бюджет не выше {budget}</span><span>✓ Не более 2 мер в направлении</span><span>✓ Район и совместимость мер проверены</span></div>{validationMessage && <p className="validation-message" role="alert">{validationMessage}</p>}<button className="primary-button simulate-button" onClick={simulate} disabled={decisions.length !== REQUIRED_DECISIONS || simulating}>Рассчитать последствия <span>→</span></button><small className="scenario-fineprint">Стоимость и эффекты загружены из Simulation API.</small></aside></div></section>

        <section className="result-section" id="result"><div className="section-intro"><div><p className="eyebrow">ШАГ 03 · ПОСЛЕДСТВИЯ</p><h2>Что изменится после решений?</h2></div><span className="section-note">Сначала расчёт, затем интерпретация</span></div>{result ? <div className="result-layout"><div className="result-primary"><div className="result-score-line"><div><span>ASTANA QUALITY OF LIFE SCORE</span><strong>{result.baselineScore.toFixed(2)} <i>→</i> {result.score.toFixed(2)}</strong><p>Изменение: {(result.score - result.baselineScore >= 0 ? '+' : '') + (result.score - result.baselineScore).toFixed(2)} пункта</p></div><div className="result-trend">↗</div></div><div className="result-facts"><span>Критические показатели <b>{result.criticalBefore} → {result.criticalAfter}</b></span><span>Синергии мер <b>{result.synergies}</b></span></div><h3>Изменение по районам</h3><div className="result-districts">{result.districts.map((district) => <div className="result-district" key={district.id}><span>{district.name}</span><div className="result-bar"><span style={{ width: `${district.nextScore}%` }}/></div><strong>{district.nextScore.toFixed(1)}</strong><small>+{district.delta.toFixed(1)}</small></div>)}</div></div><div className="advisor-panel"><span className="advisor-kicker">✦ РАЗБОР СЦЕНАРИЯ</span><h3>Последствия вашего выбора</h3><p>Наибольшее изменение получает район <strong>{highestGain?.name}</strong>: +{highestGain?.delta.toFixed(1)} к районному индексу.</p><p>Самым слабым после мер остаётся <strong>{weakestAfter?.name}</strong> с показателем {weakestAfter?.nextScore.toFixed(1)}. Это помогает увидеть, где сохраняется дисбаланс.</p><p>Из бюджета использовано <strong>{result.spent} из {budget}</strong> единиц. Остаётся {budget - result.spent}.</p>{result.explanation.status === 'available' && result.explanation.text && <p className="advisor-ai-text">{result.explanation.text}</p>}<div className="advisor-disclaimer">Сводка построена по серверному расчёту. {result.explanation.reason ?? (result.explanation.status === 'available' ? 'AI Advisor объясняет результат модели.' : '')}</div><button className="outline-button" onClick={() => scrollTo('decisions')}>Изменить решения <span>→</span></button><button className="link-button" onClick={startAgain}>Начать новый сценарий</button></div></div> : <div className="result-empty"><div className="result-empty-mark">◎</div><h3>Последствия появятся здесь</h3><p>Добавьте пять решений, затем запустите расчёт. Вы увидите изменение оценки и каждого района.</p><button className="outline-button" onClick={() => scrollTo('decisions')}>Перейти к решениям <span>→</span></button></div>}</section>

        {result && <IndicatorComparison result={result} indicators={model.raw.indicators} selectedId={selectedDistrictId} onSelect={setSelectedDistrictId}/>}

        <section className="principles-section" id="principles"><p className="eyebrow">ПРИНЦИП ПРОДУКТА</p><h2>Человек решает. Модель считает. AI объясняет.</h2><div className="principle-grid"><div><span>01 / ЧЕЛОВЕК</span><h3>Выбор остаётся за вами</h3><p>Сравнивайте направления и районы при ограниченном бюджете.</p></div><div><span>02 / МОДЕЛЬ</span><h3>Числа воспроизводимы</h3><p>Одинаковый сценарий даёт одинаковый расчёт последствий.</p></div><div><span>03 / AI</span><h3>Объяснение компромиссов</h3><p>AI получает рассчитанные результаты и помогает их понять.</p></div></div></section>
        <footer className="footer"><span>AKIM AI · КОНЦЕПТ СИТУАЦИОННОГО ЦЕНТРА</span><span>Синтетические данные · Не прогноз реальных городских решений</span></footer>
      </div>
    </main>
  </div>
}
