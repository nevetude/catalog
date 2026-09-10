# Catalog

FastAPI + SQLite каталог фильмов/сериалов с импортом из TMDB. Фронт — ванильные JS-модули, без сборки.

## Карта кода

- `app/media.py` — ядро: фильтры→SQL, карточки, детали, опции фильтров (`/api/filters`)
- `app/db.py` — схема SQLite (создаётся с нуля, миграций нет), пул настроек PRAGMA
- `app/auth.py` — pbkdf2, сессии; `app/iso.py` — ISO-словари из `app/data/iso/*.json`
- `app/routers/` — auth, catalog (листинги/детали/компании), library
- `scripts/import_*.py` — импорт TMDB; `scripts/import_base.py` — каркас + retry
- `static/js/filters.js` — вся логика фильтров (аккордеоны, порядки чекбоксов, auto-apply)
- `static/js/pages/` — постраничные модули; `core.js` — общие утилиты
- `static/css/style.css` — единый файл стилей; `static/assets/flags/` — флаги стран (svg)
- `data/` — только изменяемое: `catalog.db` (создаётся при старте) и `lists/` (входы импорта)

## Соглашения

- Фильтры: один параметр на фасет CSV (`countries`, `type`, `companies`...), SQL строится в `media_where`.
- Флаги контента — BOOLEAN колонки, заполняет импортёр из keywords (`flags()` в import_base).
- Типы фильмов: `Movie` / `Short` / `TV Movie` (genre "TV Movie").
- Чекбоксы фильтров показываются только если значение есть в текущем наборе данных.
- Постеры w500, стиллы превью w780 / лайтбокс original, логотипы w45.

## Команды

- `make dev` — запуск локально; `make test` — pytest; `make lint` — ruff
- Импорт: `docker exec catalog python scripts/import_movies.py` (idempotent)
- Тесты создают чистую БД через `CATALOG_DB_PATH`; живут в `tests/test_app.py`

## Не читать

`data/` (пользовательские NDJSON-списки), `.venv*`, `*.db`, `uv.lock` — служебные/пользовательские.
