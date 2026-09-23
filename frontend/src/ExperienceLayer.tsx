import { useEffect, useState } from 'react'
import './experience.css'

type Page = 'welcome' | 'center' | 'decisions' | 'result' | 'map' | 'compare'
type Tip = { title: string; body: string; target: string }

const tips: Record<Page, Tip[]> = {
  welcome: [
    { title: 'Начните с карты', body: 'Наведите курсор на карту и нажмите на район. Метки показывают его текущие показатели.', target: '.welcome-card .schematic-map' },
    { title: 'Перейдите к обзору', body: 'Кнопка «Начать игру» откроет пять районов и их проблемные показатели.', target: '.welcome .primary' },
  ],
  center: [
    { title: 'Сравните районы', body: 'Выберите район в списке или на карте. Справа появятся его слабые показатели.', target: '.district-list' },
    { title: 'Посмотрите показатели', body: 'Карточки ниже карты показывают значения по всем направлениям для выбранного района.', target: '.indicator-grid' },
    { title: 'Соберите план', body: 'Когда выберете район для изучения, откройте каталог мер.', target: '.dashboard .section-heading .primary' },
  ],
  decisions: [
    { title: 'Выберите район', body: 'Для районной меры сначала укажите район. Для городской меры выбор района не нужен.', target: '.catalog-toolbar' },
    { title: 'Соберите пять мер', body: 'Нажимайте «Добавить» на карточках. Слева обновляются счётчик и остаток бюджета.', target: '.measure-list' },
    { title: 'Запустите расчёт', body: 'Кнопка SIMULATE станет доступна, когда выбраны пять совместимых мер в пределах бюджета.', target: '.guidance .primary' },
  ],
  result: [
    { title: 'Сравните до и после', body: 'Здесь показаны значения, которые вернул Simulation Engine, включая изменения по районам.', target: '.score-panel' },
    { title: 'Сохраните варианты', body: 'Сохраните расчёт в A, измените план и сохраните второй результат в B.', target: '.compare-actions' },
    { title: 'Изучите динамику', body: 'Откройте карту последствий, чтобы увидеть эффект по кварталам.', target: '.advisor-panel .primary' },
  ],
  map: [
    { title: 'Переключайте кварталы', body: 'Нажмите Q0–Q8 и следите, когда меры начинают влиять на город.', target: '.quarter-buttons' },
    { title: 'Выберите район', body: 'Нажмите район на карте или в списке. Справа появятся его показатели до и после.', target: '.map-result .schematic-map' },
  ],
  compare: [
    { title: 'Сопоставьте планы', body: 'Сравните Score, бюджет, критические показатели и изменения по каждому району.', target: '.compare-grid' },
    { title: 'Уточните сценарий', body: 'Кнопка внизу каждого столбца вернёт выбранные меры в редактор.', target: '.compare-column .secondary' },
  ],
}

export function ExperienceLayer({ page, chosen, required }: { page: Page; chosen: number; required: number }) {
  const [open, setOpen] = useState(() => {
    try { return sessionStorage.getItem('akim-guide-hidden') === '0' }
    catch { return false }
  })
  const [step, setStep] = useState(0)
  const current = tips[page]
  const tip = current[Math.min(step, current.length - 1)]

  useEffect(() => { setStep(0) }, [page])
  useEffect(() => {
    if (page === 'decisions' && chosen === required) setStep(2)
    else if (page === 'decisions' && chosen > 0) setStep(currentStep => currentStep === 0 ? 1 : currentStep)
  }, [page, chosen, required])
  useEffect(() => {
    if (!open) return
    const target = document.querySelector(tip.target)
    target?.classList.add('guide-target')
    return () => target?.classList.remove('guide-target')
  }, [open, page, tip.target])

  useEffect(() => {
    const media = window.matchMedia('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)')
    if (!media.matches) return
    let frame = 0
    const move = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse') return
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const x = event.clientX / window.innerWidth - 0.5
        const y = event.clientY / window.innerHeight - 0.5
        document.documentElement.style.setProperty('--scene-tilt-x', `${(-y * 3).toFixed(2)}deg`)
        document.documentElement.style.setProperty('--scene-tilt-y', `${(x * 3).toFixed(2)}deg`)
        document.documentElement.style.setProperty('--scene-glow-x', `${((x + 0.5) * 100).toFixed(1)}%`)
        document.documentElement.style.setProperty('--scene-glow-y', `${((y + 0.5) * 100).toFixed(1)}%`)
      })
    }
    const reset = () => {
      cancelAnimationFrame(frame)
      document.documentElement.style.setProperty('--scene-tilt-x', '0deg')
      document.documentElement.style.setProperty('--scene-tilt-y', '0deg')
    }
    window.addEventListener('pointermove', move, { passive: true })
    window.addEventListener('blur', reset)
    return () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('blur', reset)
      reset()
    }
  }, [])

  const toggle = (visible: boolean) => {
    setOpen(visible)
    try { sessionStorage.setItem('akim-guide-hidden', visible ? '0' : '1') }
    catch { /* The guide still works without browser storage. */ }
  }
  const reveal = () => {
    const target = document.querySelector(tip.target)
    target?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' })
  }

  if (!open) return <button className="guide-launcher" onClick={() => toggle(true)} aria-label="Открыть подсказки">Подсказки</button>
  return <aside className="experience-guide" aria-label="Подсказки по сайту">
    <div className="guide-head"><span>ПОДСКАЗКИ ДЛЯ ПРОХОЖДЕНИЯ</span><button onClick={() => toggle(false)} aria-label="Скрыть подсказки">×</button></div>
    <div className="guide-progress" aria-label={`Подсказка ${step + 1} из ${current.length}`}>{current.map((_, index) => <button key={index} className={step === index ? 'active' : ''} onClick={() => setStep(index)} aria-label={`Подсказка ${index + 1}`}/>)}</div>
    <div className="guide-copy" aria-live="polite"><small>ШАГ {step + 1} / {current.length}{page === 'decisions' ? ` · ВЫБРАНО ${chosen}/${required}` : ''}</small><h3>{tip.title}</h3><p>{tip.body}</p></div>
    <div className="guide-actions"><button onClick={reveal}>Показать на экране</button><button onClick={() => setStep((step + 1) % current.length)}>Далее</button></div>
  </aside>
}
