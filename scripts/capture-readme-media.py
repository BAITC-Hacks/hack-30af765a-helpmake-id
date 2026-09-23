"""Capture the live Akim UI without replacing API data or editing displayed values.

Only README.md and docs/media are updated. No application code is changed.
Run with playwright and Pillow installed, and Chromium available to Playwright.
"""
import asyncio
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'media'
SITE = 'https://helpmake-id.live/'
SCENARIO = [('M7', 'nura'), ('M8', 'nura'), ('M10', 'nura'), ('M12', None), ('M5', 'saryarka')]


def gif(name, frames, durations):
    images = []
    for frame in frames:
        image = Image.open(io.BytesIO(frame)).convert('RGB')
        image = image.resize((1000, round(image.height * 1000 / image.width)), Image.Resampling.LANCZOS)
        images.append(image.quantize(colors=128, method=Image.Quantize.MEDIANCUT))
    images[0].save(OUT / name, save_all=True, append_images=images[1:],
                   duration=durations, loop=0, optimize=True, disposal=2)


def insert_after_paragraph(text, heading, block):
    if text.count(heading) != 1:
        raise ValueError(f'Expected one README heading: {heading}')
    start = text.index(heading) + len(heading)
    end = text.find('\n\n', start + 1)
    if end < 0:
        raise ValueError(f'No paragraph after {heading}')
    return text[:end] + '\n\n' + block + text[end:]


def update_readme():
    target = ROOT / 'README.md'
    text = target.read_text(encoding='utf-8')
    # A repeated capture updates its own blocks, leaving other content intact.
    text = re.sub(r'\n*<!-- AKIM-MEDIA:[\w-]+:START -->.*?<!-- AKIM-MEDIA:[\w-]+:END -->\n*', '\n\n', text, flags=re.S)
    def block(key, body):
        return f'<!-- AKIM-MEDIA:{key}:START -->\n{body}\n<!-- AKIM-MEDIA:{key}:END -->'
    hero = block('result', '## Реальный интерфейс\n\n![Результат симуляции: индекс города, изменения районов и AI Advisor](docs/media/simulation-result.png)\n\n*Снимок работающего приложения. Числа относятся к конкретному показанному сценарию; это не макет и не прогноз реальных показателей города.*')
    if text.count('## Проблема') != 1:
        raise ValueError('README has changed: missing unique problem section')
    text = text.replace('## Проблема', hero + '\n\n## Проблема', 1)
    demo = block('flow', '### Демонстрация в GIF\n\n![Путь пользователя: обзор города, выбор пяти мер и результат расчёта](docs/media/simulation-flow.gif)\n\n*Ускоренная последовательность реальных экранов сайта. [Открыть GIF отдельно](docs/media/simulation-flow.gif).*')
    if text.count('## Соответствие заданию HackAlem') != 1:
        raise ValueError('README has changed: missing unique requirements section')
    text = text.replace('## Соответствие заданию HackAlem', demo + '\n\n## Соответствие заданию HackAlem', 1)
    text = insert_after_paragraph(text, '### 🏙️ Situation Center', block('center', '![Обзор города: районы, схема и исходные показатели](docs/media/situation-center.png)\n\n*Карта и показатели загружены из приложения; схема не является официальной картой границ районов.*'))
    text = insert_after_paragraph(text, '### 💰 Управление ограниченным бюджетом', block('selection', '![Выбор инициатив: бюджет, выбранные меры и ограничения сценария](docs/media/initiative-selection.png)'))
    text = insert_after_paragraph(text, '### ⏱️ Временная динамика', block('quarters', '![Переключение кварталов Q0–Q8 и изменение показателей районов](docs/media/quarter-dynamics.gif)\n\n*[Открыть поквартальную демонстрацию отдельно](docs/media/quarter-dynamics.gif).*'))
    text = insert_after_paragraph(text, '### 🤖 Grounded AI Advisor', block('advisor', '<img src="docs/media/advisor.png" alt="AI Advisor: фактическое состояние панели объяснения результата" width="380">\n\n*Показан ответ или явное состояние недоступности, фактически полученное при записи. Источник и время съёмки: [описание медиа](docs/media/README.md).*'))
    target.write_text(text, encoding='utf-8')


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    flow = []
    result_json = None
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 1440, 'height': 1080}, device_scale_factor=1, locale='ru-RU')
        page = await context.new_page()
        page.set_default_timeout(30000)
        response = await page.goto(SITE, wait_until='domcontentloaded', timeout=60000)
        if response is None or response.status >= 400:
            raise RuntimeError('Live site could not be loaded; refusing to publish blank media')
        await page.locator('.app-shell[data-page="welcome"]').wait_for(timeout=60000)
        await page.evaluate('document.fonts.ready')
        await page.wait_for_timeout(700)
        flow.append(await page.screenshot())
        await page.get_by_role('button', name=re.compile('Начать игру')).click()
        await page.locator('.app-shell[data-page="center"]').wait_for()
        await page.locator('.district-item').filter(has_text='Нура').click()
        await page.wait_for_timeout(700)
        await page.screenshot(path=str(OUT / 'situation-center.png'))
        flow.append(await page.screenshot())
        await page.get_by_role('button', name=re.compile('Создать сценарий')).click()
        await page.locator('.app-shell[data-page="decisions"]').wait_for()
        for measure_id, district in SCENARIO:
            if district:
                await page.locator('.catalog-toolbar select').select_option(district)
            card = page.locator('.measure-card').filter(has=page.locator('.measure-id', has_text=re.compile('^' + measure_id + '$')))
            await card.get_by_role('button', name=re.compile('Добавить')).click()
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(350)
            flow.append(await page.screenshot())
        await page.screenshot(path=str(OUT / 'initiative-selection.png'))
        async with page.expect_response(lambda r: r.request.method == 'POST' and '/api/v1/simulate' in r.url) as calculation:
            await page.locator('.guidance').get_by_role('button', name=re.compile('SIMULATE')).click()
        result_json = await (await calculation.value).json()
        if result_json.get('valid') is not True:
            raise RuntimeError('The live backend rejected the capture scenario')
        await page.locator('.app-shell[data-page="result"]').wait_for()
        await page.locator('.advisor-copy, .advisor-unavailable').first.wait_for(timeout=75000)
        await page.evaluate('window.scrollTo(0, 0)')
        await page.wait_for_timeout(500)
        await page.locator('.result-grid').screenshot(path=str(OUT / 'simulation-result.png'))
        await page.locator('.advisor-panel').screenshot(path=str(OUT / 'advisor.png'))
        await page.evaluate('window.scrollTo(0, 0)')
        flow.append(await page.screenshot())
        advisor_status = 'available' if await page.locator('.advisor-copy').count() else 'unavailable'
        gif('simulation-flow.gif', flow, [1300, 1500] + [750] * 5 + [3200])
        await page.locator('.advisor-panel').get_by_role('button', name=re.compile('Посмотреть динамику')).click()
        await page.locator('.app-shell[data-page="map"]').wait_for()
        await page.locator('.district-item').filter(has_text='Нура').click()
        quarters = []
        for q in [0, 2, 4, 6, 8]:
            await page.locator('.quarter-buttons button').filter(has_text=re.compile('^Q' + str(q) + r'\b')).click()
            await page.evaluate('window.scrollTo(0, 0)')
            await page.wait_for_timeout(600)
            quarters.append(await page.screenshot())
        gif('quarter-dynamics.gif', quarters, [1500, 1000, 1000, 1000, 2500])
        await browser.close()
    files = ['situation-center.png', 'initiative-selection.png', 'simulation-result.png', 'advisor.png', 'simulation-flow.gif', 'quarter-dynamics.gif']
    metadata = {
        'source': SITE, 'capture_utc': datetime.now(timezone.utc).isoformat(),
        'method': 'Playwright screenshots of the live site; no API mocking, DOM content rewriting, or fabricated numbers',
        'advisor_status': advisor_status,
        'scenario': result_json['decisions'],
        'score': result_json['score'], 'baseline_score': result_json['baseline_score'],
        'dataset_hash': result_json.get('dataset_hash'),
        'assets': {name: {'bytes': (OUT/name).stat().st_size, 'sha256': hashlib.sha256((OUT/name).read_bytes()).hexdigest()} for name in files},
    }
    (OUT/'capture.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT/'README.md').write_text('# Медиа для README\n\nКаждый PNG и GIF — отдельный файл. Они сняты с работающего сайта https://helpmake-id.live/, а не нарисованы генератором изображений.\n\nGIF собраны из последовательных реальных экранов, длительность показа сокращена для README. Значения в интерфейсе не редактируются.\n\nИсточник, время, сценарий, статус AI и контрольные суммы: [capture.json](capture.json). Состояние приложения может отличаться от ранее присланной записи с iPad, поскольку это новая съёмка сайта.\n\nПовторная съёмка вручную: `python scripts/capture-readme-media.py`. Скрипт обновляет README только после успешного создания всех файлов.\n', encoding='utf-8')
    for name in files:
        with Image.open(OUT/name) as im:
            im.verify()
    update_readme()
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
