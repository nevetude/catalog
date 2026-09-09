# Catalog 5.0

FastAPI + SQLite каталог фильмов и сериалов с импортом данных TMDB.

## Архитектура

- Единый медиа-слой `app/media.py`: одна декларативная модель фильтров обслуживает
  все листинги (каталог, библиотека, фильмография, компания, коллекция) для обеих
  таблиц — семантика фильтров существует ровно один раз, в виде SQL.
- `app/db.py` — схема SQLite (создаётся с нуля), пул PRAGMA, bootstrap админа.
- `app/auth.py` — pbkdf2-хэши, сессии (legacy-хэши апгрейдятся при логине).
- Фронтенд — ванильные JS-модули без сборки: `core.js`, `cards.js`, `listing.js`,
  `filters.js` и постраничные модули в `static/js/pages/`.
- Библиотека пользователя: произвольные папки, элемент может лежать в нескольких.

## Запуск через Docker

```bash
# проверь TMDB_API_KEY в .env
make docker-up
```

Приложение: `http://localhost:8000`

## Локальный запуск

```bash
make sync        # uv sync
make dev         # uvicorn с reload на :8000
```

## Импорт

```bash
make import-movies    # фильмы из data/lists/movies.ndjson
make import-shows     # сериалы из data/lists/shows.ndjson
make import-all
```

Списки ID берутся из NDJSON-файлов в `data/lists/` (поля `id`, `title`/`name`,
`popularity`). Импорт идемпотентен (upsert по TMDB id) — можно безопасно
перезапускать; в конце прогона печатается список упавших ID.

Параметры клиента — в `scripts/import_base.py`:

- `REQUEST_CONCURRENCY`
- `REQUEST_INTERVAL`
- `RETRY_COUNT`
- `BATCH_SIZE`

## Проверка

```bash
make test
make lint
```

## Структура

```text
app/
  config.py         константы, пути, размеры картинок TMDB
  db.py             SQLite connection, схема
  media.py          единый слой листингов: фильтры -> SQL, карточки, детали
  auth.py           pbkdf2-хэши, сессии, зависимости запросов
  data/iso/         ISO-справочники стран и языков (json)
  routers/
    auth.py         /api/auth/*, /api/me
    catalog.py      /api/catalog, /api/filters, детали, персоны, компании, коллекции
    library.py      /api/library/* — папки и элементы пользователя

scripts/
  import_base.py    каркас импорта: HTTP-клиент, retry, savepoints, upsert персон
  import_movies.py  фильмы
  import_shows.py   сериалы (+ эпизоды)

static/             всё, что отдаётся браузеру
  pages/            HTML-каркасы страниц
  js/               core, cards, listing, filters
  js/pages/         постраничные модули
  css/              style.css
  assets/flags/     флаги стран (svg)

data/               только изменяемое (gitignored)
  lists/            NDJSON-списки для импорта
  catalog.db        база (создаётся при старте)
```

База по умолчанию — `data/catalog.db`, переопределяется переменной `CATALOG_DB_PATH`.
