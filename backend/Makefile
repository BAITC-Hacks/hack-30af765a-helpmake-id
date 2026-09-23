PYTHON := .venv/bin/python
PIP := .venv/bin/pip
UVICORN := .venv/bin/uvicorn
PYTEST := .venv/bin/pytest
RUFF := .venv/bin/ruff
ALEMBIC := .venv/bin/alembic

.DEFAULT_GOAL := help

.PHONY: help install dev test lint format check migration migrate up down logs

help:
	@echo "Available commands:"
	@echo "  make install          Install all dependencies"
	@echo "  make dev              Start development server with auto-reload"
	@echo "  make test             Run tests with coverage"
	@echo "  make lint             Run Ruff linter"
	@echo "  make format           Format code with Ruff"
	@echo "  make check            Lint + format check (no writes)"
	@echo "  make migration M=... Generate a new Alembic migration"
	@echo "  make migrate          Apply all pending migrations"
	@echo "  make up               Start Docker services (postgres + backend)"
	@echo "  make down             Stop Docker services"
	@echo "  make logs             Tail Docker service logs"

install:
	$(PIP) install -e ".[dev]"

dev:
	$(UVICORN) src.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTEST) tests/ -v

lint:
	$(RUFF) check src/ tests/

format:
	$(RUFF) format src/ tests/
	$(RUFF) check --fix src/ tests/

check:
	$(RUFF) format --check src/ tests/
	$(RUFF) check src/ tests/

migration:
	@if [ -z "$(M)" ]; then echo "Usage: make migration M=\"description\""; exit 1; fi
	$(ALEMBIC) revision --autogenerate -m "$(M)"

migrate:
	$(ALEMBIC) upgrade head

# Docker helpers
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f
