# Akim AI — ситуационный центр

Рабочий локальный MVP по [Lean Canvas](https://app.notion.com/p/Lean-Canvas-Akim-AI-3e44da4969ea81848940ebcb06f81e5c) и [проекту команды](https://github.com/BAITC-Hacks/hack-30af765a-helpmake-id). Исходный набор `simulation.json` и схема API взяты из GitHub на коммите `2b28598`.

Путь пользователя: базовые показатели пяти районов → ровно пять решений при бюджете 100 → серверная проверка → детерминированный расчёт → Score, изменения индикаторов и разбор результата.

## Запуск локально

Нужны Python 3.12+ и Node.js с npm. Запустите backend и frontend в разных терминалах.

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```sh
cd frontend
npm install
npm run dev
```

Откройте адрес Vite, обычно `http://localhost:5173/`. Если порт или адрес API отличается, задайте `VITE_API_URL` по примеру в `frontend/.env.example`. Для CORS укажите адрес frontend в `backend/.env` через `FRONTEND_ORIGIN`.

## API

| Метод | Путь | Назначение |
| --- | --- | --- |
| GET | `/api/v1/health` | Доступность backend |
| GET | `/api/v1/simulation/data` | Районы, индикаторы, меры и ограничения |
| POST | `/api/v1/simulation` | Проверка и расчёт сценария |

Пример тела POST:

```json
{
  "decisions": [
    { "measure_id": "M1", "district_id": "Нура" },
    { "measure_id": "M2", "district_id": null },
    { "measure_id": "M7", "district_id": "Нура" },
    { "measure_id": "M10", "district_id": "Есиль" },
    { "measure_id": "M12", "district_id": null }
  ]
}
```

API возвращает базовый и новый Score, показатели каждого района до и после, вклад каждой меры, сработавшие синергии и количество критических показателей. Невалидный сценарий получает HTTP 400 с кодом и сообщением; ошибки формы запроса получают HTTP 422. Интерактивная документация доступна на `http://127.0.0.1:8000/docs`.

## Правила модели

- Бюджет 100, ровно пять различных инициатив.
- Для районной меры обязателен существующий район; городская мера не принимает район.
- Не более двух мер в одном направлении; несовместимости берутся из датасета.
- Горизонт — восемь кварталов; эффект меры с лагом `L` умножается на `(8 - L) / 8`.
- Числа индикаторов ограничиваются интервалом 0–100. Score учитывает средневзвешенный результат города, слабейший район и число индикаторов строго ниже 40.
- Одинаковый набор решений даёт одинаковый числовой результат независимо от порядка.

Базовый Score из [backend/data/simulation.json](backend/data/simulation.json) равен **52.56**. Данные синтетические и не отражают реальное состояние Астаны. Точки на карте приблизительны, подложка OpenStreetMap требует интернета.

## AI Advisor

Числа всегда рассчитывает Simulation Engine. Если в `backend/.env` задан `OPENAI_API_KEY`, сервер отправляет рассчитанную сводку в OpenAI Responses API и возвращает текст в `ai_explanation`. Модель по умолчанию — `gpt-4.1-mini`; её можно изменить через `OPENAI_MODEL`. Ключ хранится только на backend. При отсутствии ключа или ошибке провайдера ответ содержит `status = unavailable`, а интерфейс показывает разбор по числам. AI не меняет Score.

## Проверка

```sh
cd backend
.venv/bin/python -m unittest discover -s tests -v
```

```sh
cd frontend
npm run build
```

Исходные данные и схема симуляции взяты из этого репозитория; работающий интерфейс и API находятся в `frontend/` и `backend/app/`.
