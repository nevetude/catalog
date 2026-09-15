"""Application constants, paths, TMDB image prefixes."""

from __future__ import annotations

import os
from pathlib import Path

VERSION = "5.0.0"

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
DB_PATH = Path(os.getenv("CATALOG_DB_PATH", ROOT / "data" / "catalog.db"))

COOKIE = "catalog_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 365
DEFAULT_FOLDERS = ("Watchlist", "Watched")

TMDB_IMAGE = "https://image.tmdb.org/t/p"
POSTER = f"{TMDB_IMAGE}/w500"
BACKDROP = f"{TMDB_IMAGE}/w1280"
BACKDROP_ORIG = f"{TMDB_IMAGE}/original"
STILL = f"{TMDB_IMAGE}/w780"
STILL_EP = f"{TMDB_IMAGE}/w300"

CERT_ORDER = [
    "G", "PG", "PG-13", "R", "NC-17", "NR",
    "TV-Y", "TV-Y7", "TV-Y7-FV", "TV-G", "TV-PG", "TV-14", "TV-MA",
]
