"""SQLite connection, schema and startup bootstrap."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from app.config import DB_PATH, DEFAULT_FOLDERS, SESSION_MAX_AGE

SCHEMA = """
CREATE TABLE IF NOT EXISTS movies (
    id                    INTEGER PRIMARY KEY,
    type                  TEXT DEFAULT 'Movie',
    title                 TEXT,
    original_title        TEXT NOT NULL,
    status                TEXT,
    adult                 BOOLEAN,
    softcore              BOOLEAN,
    gay                   BOOLEAN,
    lesbian               BOOLEAN,
    anime                 BOOLEAN,
    donghua               BOOLEAN,
    aeni                  BOOLEAN,
    amerime               BOOLEAN,
    certification         TEXT,
    release_date          TEXT,
    runtime               INTEGER DEFAULT 0,
    origin_country        TEXT,
    original_language     TEXT,
    languages             TEXT,
    spoken_languages      TEXT,
    genres                TEXT,
    popularity            REAL DEFAULT 0,
    vote_average          REAL DEFAULT 0,
    vote_count            INTEGER DEFAULT 0,
    budget                INTEGER DEFAULT 0,
    revenue               INTEGER DEFAULT 0,
    imdb_id               TEXT,
    homepage              TEXT,
    belongs_to_collection INTEGER,
    collection_name       TEXT,
    production_countries  TEXT,
    production_companies  TEXT,
    poster_path           TEXT,
    backdrop_path         TEXT,
    tagline               TEXT,
    overview              TEXT,
    keywords              TEXT,
    updated_at            TEXT
);

CREATE TABLE IF NOT EXISTS shows (
    id                   INTEGER PRIMARY KEY,
    type                 TEXT DEFAULT 'TV',
    name                 TEXT,
    original_name        TEXT NOT NULL,
    status               TEXT,
    in_production        BOOLEAN,
    adult                BOOLEAN,
    softcore             BOOLEAN,
    gay                  BOOLEAN,
    lesbian              BOOLEAN,
    anime                BOOLEAN,
    donghua              BOOLEAN,
    aeni                 BOOLEAN,
    amerime              BOOLEAN,
    certification        TEXT,
    first_air_date       TEXT,
    last_air_date        TEXT,
    episode_run_time     TEXT,
    number_of_seasons    INTEGER,
    number_of_episodes   INTEGER,
    origin_country       TEXT,
    original_language    TEXT,
    languages            TEXT,
    spoken_languages     TEXT,
    genres               TEXT,
    popularity           REAL,
    vote_average         REAL,
    vote_count           INTEGER,
    homepage             TEXT,
    networks             TEXT,
    production_countries TEXT,
    production_companies TEXT,
    poster_path          TEXT,
    backdrop_path        TEXT,
    tagline              TEXT,
    overview             TEXT,
    seasons              TEXT,
    keywords             TEXT,
    updated_at           TEXT
);

CREATE TABLE IF NOT EXISTS episodes (
    id             INTEGER PRIMARY KEY,
    show_id        INTEGER NOT NULL,
    season_number  INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    name           TEXT,
    overview       TEXT,
    air_date       TEXT,
    runtime        INTEGER DEFAULT 0,
    still_path     TEXT,
    vote_average   REAL DEFAULT 0,
    vote_count     INTEGER DEFAULT 0,
    FOREIGN KEY (show_id) REFERENCES shows(id),
    UNIQUE (show_id, season_number, episode_number)
);

CREATE TABLE IF NOT EXISTS backdrops (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    media_type TEXT NOT NULL,
    media_id   INTEGER NOT NULL,
    file_path  TEXT NOT NULL,
    width      INTEGER DEFAULT 0,
    height     INTEGER DEFAULT 0,
    UNIQUE (media_type, media_id, file_path)
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS library_folders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    name       TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS library_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id  INTEGER NOT NULL,
    media_type TEXT NOT NULL,
    media_id   INTEGER NOT NULL,
    added_at   TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (folder_id) REFERENCES library_folders(id) ON DELETE CASCADE,
    UNIQUE (folder_id, media_type, media_id)
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_movies_votes ON movies(vote_count DESC);
CREATE INDEX IF NOT EXISTS idx_shows_votes ON shows(vote_count DESC);
CREATE INDEX IF NOT EXISTS idx_movies_type ON movies(type);
CREATE INDEX IF NOT EXISTS idx_lib_items ON library_items(folder_id);
CREATE INDEX IF NOT EXISTS idx_lib_items_media ON library_items(media_type, media_id, folder_id);
CREATE INDEX IF NOT EXISTS idx_movies_release_date ON movies(release_date);
CREATE INDEX IF NOT EXISTS idx_shows_first_air_date ON shows(first_air_date);
CREATE INDEX IF NOT EXISTS idx_movies_popularity ON movies(popularity DESC);
CREATE INDEX IF NOT EXISTS idx_shows_popularity ON shows(popularity DESC);
CREATE INDEX IF NOT EXISTS idx_movies_rating ON movies(vote_average DESC, vote_count DESC);
CREATE INDEX IF NOT EXISTS idx_shows_rating ON shows(vote_average DESC, vote_count DESC);
CREATE INDEX IF NOT EXISTS idx_movies_runtime ON movies(runtime);
CREATE INDEX IF NOT EXISTS idx_shows_episodes ON shows(number_of_episodes);
CREATE INDEX IF NOT EXISTS idx_episodes_show_season
    ON episodes(show_id, season_number, episode_number);
CREATE INDEX IF NOT EXISTS idx_movies_collection ON movies(belongs_to_collection);
CREATE INDEX IF NOT EXISTS idx_movies_companies ON movies(production_companies);
CREATE INDEX IF NOT EXISTS idx_shows_companies ON shows(production_companies);
CREATE INDEX IF NOT EXISTS idx_backdrops_media ON backdrops(media_type, media_id);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA cache_size = -32768")
    return conn


@contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_folders(conn: sqlite3.Connection, user_id: int) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO library_folders (user_id, name) VALUES (?, ?)",
        [(user_id, name) for name in DEFAULT_FOLDERS],
    )


def init_db() -> None:
    """Create the schema, drop removed tables, bootstrap the admin."""
    from app.auth import hash_password  # imported here to avoid a circular import

    with get_db() as conn:
        conn.executescript(SCHEMA)
        conn.executescript(INDEXES)
        conn.execute("DROP TABLE IF EXISTS translations")
        conn.execute("DROP TABLE IF EXISTS credits")
        conn.execute("DROP TABLE IF EXISTS people")
        conn.execute(
            "DELETE FROM sessions WHERE created_at < datetime('now', ?)",
            (f"-{SESSION_MAX_AGE} seconds",),
        )
        admin = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
        if admin:
            admin_id = admin["id"]
        else:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES ('admin', ?)",
                (hash_password("admin"),),
            )
            admin_id = cursor.lastrowid
        ensure_folders(conn, admin_id)
