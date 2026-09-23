# Локальный запуск Akim AI

Ниже описан запуск всего проекта: PostgreSQL и backend работают в Docker Compose, frontend — через Vite на компьютере. Команды выполняются из корня репозитория, если не указано другое.

## Что понадобится

- Docker с запущенным Docker Engine и Compose v2 (`docker compose` или `docker-compose`).
- Node.js 20.19+ и npm для frontend.
- Свободные порты `5432`, `8000` и `5173`.

Python для основного способа запуска не требуется. Он нужен только для запуска backend вне Docker и для локальных проверок.

## 1. Проверить настройки backend

В приватном репозитории уже находится `backend/.env` с настроенным PostgreSQL и ключом AI-провайдера. После клонирования ничего копировать или заполнять не требуется. Пустые неиспользуемые ключи из этого файла удалены.

Если вы меняете пароль или настройки провайдера, редактируйте `backend/.env` до запуска контейнеров. Не публикуйте этот файл вне приватного репозитория: в нём есть действующий API-ключ. Для собственных настроек можно взять `backend/.env.example` как образец.

## 2. Запустить PostgreSQL и backend

```bash
cd backend
docker compose up --build -d
docker compose ps
```

Compose сначала запускает PostgreSQL, затем применяет миграции сервисом `migrate` и запускает backend. Если у вас доступна команда `docker-compose`, но нет `docker compose`, замените её во всех командах гайда на `docker-compose`.

Проверьте готовность API:

```bash
curl http://127.0.0.1:8000/api/v1/ready
```

Ожидается ответ со `status: "ok"` и `dataset_version`. Swagger UI доступен по адресу <http://127.0.0.1:8000/docs>.

## 3. Запустить frontend

Откройте второй терминал в корне репозитория:

```bash
cd frontend
npm ci
npm run dev
```

Откройте <http://127.0.0.1:5173>. В локальном режиме Vite направляет запросы `/api` на `http://127.0.0.1:8000`, поэтому дополнительных настроек frontend для этого способа не требуется.

## Остановка и повторный запуск

Остановите Vite сочетанием `Ctrl+C`. Для остановки контейнеров выполните из каталога `backend`:

```bash
docker compose down
```

Эта команда сохраняет данные PostgreSQL в Docker volume. При следующем запуске выполните `docker compose up -d` из `backend`, затем `npm run dev` из `frontend`. Команда `docker compose down -v` удаляет volume **вместе со всеми сохранёнными сценариями**.

## Если запуск не удался

- `POSTGRES_PASSWORD` не задан: проверьте наличие и содержимое `backend/.env` и повторите `docker compose up --build -d`.
- API `/ready` возвращает `503`: проверьте состояние сервисов командой `docker compose ps` и журналы командой `docker compose logs --tail=100 postgres migrate backend` из `backend`. Готовность зависит от PostgreSQL и завершённой миграции.
- Frontend показывает ошибку API: сначала проверьте `http://127.0.0.1:8000/api/v1/ready`, затем убедитесь, что Vite запущен без переопределения `AKIM_API_URL` и `VITE_API_BASE_URL`.
- Порт занят: освободите `5432`, `8000` или `5173` и запустите сервисы снова. Если Vite выбрал другой порт, используйте адрес, который он вывел в терминале.

## Backend вне Docker (необязательно)

Можно оставить в Docker только PostgreSQL, а backend запустить с автоперезагрузкой. Нужен Python 3.12+; из `backend` выполните:

```bash
python3 -m venv .venv
make install
docker compose up -d postgres
export DATABASE_URL="$(sed -n 's/^DATABASE_URL=//p' .env)"
make migrate
make dev
```

Команда `make dev` сама не загружает `.env`: для AI-советника при этом способе запуска также экспортируйте `AI_API_URL`, `AI_MODEL` и `AI_API_KEY` из файла в окружение процесса. Frontend запускается так же, как в шаге 3.
