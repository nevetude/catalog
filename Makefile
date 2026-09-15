.PHONY: help dev stop sync lint test import-movies import-shows import-all clean login docker-up docker-down docker-logs

help:
	@echo "make dev           — локальный сервер с --reload на :8000"
	@echo "make stop          — остановить локальный сервер"
	@echo "make sync          — uv sync (зависимости в .venv)"
	@echo "make lint | test   — ruff / pytest"
	@echo "make import-movies | import-shows | import-all"
	@echo "make clean         — удалить data/catalog.db"
	@echo "make login         — тестовый вход admin/admin"
	@echo "make docker-up | docker-down | docker-logs — докер (на случай возврата)"

dev:
	PYTHONPATH=. uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

stop:
	@pkill -f "uvicorn app.main:app" 2>/dev/null && echo "остановлен" || echo "не запущен"

sync:
	uv sync --extra dev

lint:
	uv run ruff check app scripts tests

test:
	uv run pytest -q

import-movies:
	PYTHONPATH=. uv run python scripts/import_movies.py

import-shows:
	PYTHONPATH=. uv run python scripts/import_shows.py

import-all: import-movies import-shows

clean:
	rm -f data/catalog.db data/catalog.db-wal data/catalog.db-shm

login:
	@curl -s -c /tmp/catalog_cookies.txt -X POST http://localhost:8000/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"username": "admin", "password": "admin"}' | head -c 200; echo
	@echo "Session cookie saved to /tmp/catalog_cookies.txt"

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f catalog
