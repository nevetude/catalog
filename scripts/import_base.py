"""Shared TMDB importer machinery.

Subclasses define only what differs: the list file, detail endpoints and row
mapping. Everything else — HTTP with retry/pacing, chunked fetching, savepoints,
person/credit upserts, progress output — lives here.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

REQUEST_TIMEOUT = 30.0
REQUEST_CONCURRENCY = 8
REQUEST_INTERVAL = 0.1
RETRY_COUNT = 4
BATCH_SIZE = 100

CAST_JOB = "Actor"


def _keywords(data: dict) -> list[str]:
    raw = data.get("keywords") or {}
    items = (
        raw.get("keywords")
        or raw.get("results")
        or (raw if isinstance(raw, list) else [])
    )
    return [
        k["name"]
        for k in items
        if isinstance(k, dict) and k.get("name")
    ]

def flags(keywords: list[str]) -> dict[str, bool]:
    """Keyword-derived boolean flags shared by movies and shows."""
    kws = [k.strip().lower() for k in keywords]
    exact = set(kws)
    aeni = "aeni" in exact or "korean animation" in exact
    return {
        "softcore": "softcore" in exact,
        "gay": any(t in k for k in kws for t in (
            "gay pornography", "homosexual", "male homosexuality",
            "transsexual", "tomboy")),
        "lesbian": any(t in k for k in kws for t in (
            "lesbian", "lesbianism", "women love")),
        "anime": "anime" in exact and not aeni,
        "donghua": "donghua" in exact,
        "aeni": aeni,
        "amerime": "anime inspired" in exact,
    }


def us_certification(data: dict) -> str | None:
    for country in (data.get("release_dates") or {}).get("results") or []:
        if country.get("iso_3166_1") == "US":
            for release in country.get("release_dates") or []:
                if release.get("certification"):
                    return release["certification"]
    return None


def us_tv_certification(data: dict) -> str | None:
    for country in (data.get("content_ratings") or {}).get("results") or []:
        if country.get("iso_3166_1") == "US" and (country.get("rating") or "").strip():
            return country["rating"].strip()
    return None


def upsert_person(conn, person: dict) -> None:
    if not person.get("id"):
        return
    conn.execute(
        "INSERT INTO people (id, name, profile_path, biography, birthday, place_of_birth, "
        "known_for_department, updated_at) VALUES (?,?,?,?,?,?,?,datetime('now')) "
        "ON CONFLICT(id) DO UPDATE SET name = excluded.name, "
        "profile_path = COALESCE(excluded.profile_path, people.profile_path), "
        "biography = COALESCE(excluded.biography, people.biography), "
        "birthday = COALESCE(excluded.birthday, people.birthday), "
        "place_of_birth = COALESCE(excluded.place_of_birth, people.place_of_birth), "
        "known_for_department = COALESCE(excluded.known_for_department, "
        "people.known_for_department), "
        "updated_at = datetime('now')",
        (person.get("id"), person.get("name") or "", person.get("profile_path"),
         person.get("biography"), person.get("birthday"), person.get("place_of_birth"),
         person.get("known_for_department")),
    )


def save_credits(conn, media_type: str, media_id: int, credits: dict) -> None:
    """Replace crew (filtered to known jobs) and ordered cast for one media record."""
    conn.execute("DELETE FROM credits WHERE media_type = ? AND media_id = ?",
                 (media_type, media_id))
    from app.config import CREW_JOBS
    rows: list[tuple] = []
    for crew in credits.get("crew") or []:
        job = (crew.get("job") or "").strip()
        if job in CREW_JOBS and crew.get("id"):
            upsert_person(conn, crew)
            rows.append((media_type, media_id, crew["id"], job, None, 0))
    for order, actor in enumerate(credits.get("cast") or []):
        if actor.get("id"):
            upsert_person(conn, actor)
            rows.append((media_type, media_id, actor["id"], CAST_JOB,
                         actor.get("character"), order))
    conn.executemany(
        "INSERT OR IGNORE INTO credits (media_type, media_id, person_id, job, character, ord) "
        "VALUES (?, ?, ?, ?, ?, ?)", rows,
    )


def save_backdrops(conn, media_type: str, media_id: int, backdrops: list) -> None:
    """Replace the backdrop rows for one media record."""
    conn.execute("DELETE FROM backdrops WHERE media_type = ? AND media_id = ?",
                 (media_type, media_id))
    conn.executemany(
        "INSERT OR IGNORE INTO backdrops (media_type, media_id, file_path, width, height) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (media_type, media_id, b["file_path"], b.get("width") or 0, b.get("height") or 0)
            for b in backdrops or [] if b.get("file_path")
        ],
    )


def jdump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def named_list(items: list[dict], *fields: str) -> list[dict]:
    return [{f: item.get(f) for f in fields} for item in items or []]


class TMDBClient:
    """Rate-limited HTTP client with exponential backoff on 429/5xx."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
        self.semaphore = asyncio.Semaphore(REQUEST_CONCURRENCY)
        self.rate_lock = asyncio.Lock()
        self.last_request = 0.0

    async def close(self) -> None:
        await self.client.aclose()

    async def get(self, path: str, params: dict | None = None) -> dict | None:
        params = {"api_key": API_KEY, **(params or {})}
        async with self.semaphore:
            for attempt in range(RETRY_COUNT + 1):
                async with self.rate_lock:
                    loop = asyncio.get_running_loop()
                    wait = REQUEST_INTERVAL - (loop.time() - self.last_request)
                    if wait > 0:
                        await asyncio.sleep(wait)
                    self.last_request = asyncio.get_running_loop().time()
                try:
                    response = await self.client.get(f"{BASE_URL}{path}", params=params)
                except (httpx.TimeoutException, httpx.TransportError) as error:
                    # Transient network failures (timeouts, dropped connections) hit
                    # bursts of concurrent requests; retry with the same backoff as 5xx.
                    if attempt >= RETRY_COUNT:
                        raise
                    print(f"  retry {attempt + 1}/{RETRY_COUNT} {path}: "
                          f"{type(error).__name__}: {error}")
                    await asyncio.sleep(min(2.0 ** attempt, 15.0))
                    continue
                if response.status_code == 404:
                    return None
                if response.status_code in (429, 500, 502, 503):
                    if attempt >= RETRY_COUNT:
                        response.raise_for_status()
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = float(retry_after)
                    except (TypeError, ValueError):
                        delay = 2.0 ** attempt
                    await asyncio.sleep(min(delay, 15.0))
                    continue
                response.raise_for_status()
                return response.json()
        return None


class BaseImporter(ABC):
    media_type: str          # credit media type: "movie" or "tv"
    list_file: str           # ndjson filename under data/lists/
    label: str               # progress label

    @abstractmethod
    def fetch(self, tmdb: TMDBClient, tmdb_id: int) -> dict | None:
        """Fetch the full TMDB payload for one id; None means skip."""

    @abstractmethod
    def save(self, conn, data: dict, popularity: float | None) -> None:
        """Upsert one fetched payload (and its episodes) into SQLite."""

    def load_rows(self) -> list[dict]:
        path = ROOT / "data" / "lists" / self.list_file
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    async def run(self) -> None:
        from app.db import connect, init_db

        if not API_KEY:
            raise SystemExit("Set TMDB_API_KEY in .env")
        init_db()
        rows = self.load_rows()
        print(f"Loaded {len(rows)} {self.label}")

        tmdb = TMDBClient()
        saved = skipped = errors = 0
        failed_ids: list[int] = []
        conn = connect()
        try:
            for batch_start in range(0, len(rows), BATCH_SIZE):
                batch = rows[batch_start:batch_start + BATCH_SIZE]
                results = await asyncio.gather(
                    *(self._fetch_one(tmdb, int(row["id"])) for row in batch),
                    return_exceptions=True,
                )
                for offset, (row, result) in enumerate(zip(batch, results), start=1):
                    tmdb_id = int(row["id"])
                    name = row.get("title") or row.get("name") or row.get("original_title") \
                        or row.get("original_name") or ""
                    print(f"[{batch_start + offset}/{len(rows)}] {tmdb_id} — {name}")
                    try:
                        if isinstance(result, Exception):
                            raise result
                        if result is None:
                            skipped += 1
                            print("  skipped: not found")
                            continue
                        conn.execute("SAVEPOINT item")
                        try:
                            self.save(conn, result, row.get("popularity"))
                            conn.execute("RELEASE item")
                        except Exception:
                            conn.execute("ROLLBACK TO item")
                            conn.execute("RELEASE item")
                            raise
                        saved += 1
                    except Exception as error:
                        errors += 1
                        failed_ids.append(tmdb_id)
                        print(f"  error: {type(error).__name__}: {error}")
                conn.commit()
                print(f"  batch {batch_start + len(batch)}/{len(rows)} committed")
        finally:
            conn.close()
            await tmdb.close()
        print(f"Done {self.label}: saved={saved} skip={skipped} err={errors}")
        if failed_ids:
            print(f"Failed ids (re-run the importer to retry, it is idempotent): "
                  f"{', '.join(map(str, failed_ids))}")

    async def _fetch_one(self, tmdb: TMDBClient, tmdb_id: int) -> dict | None:
        return await self.fetch(tmdb, tmdb_id)

    def execute(self) -> None:
        asyncio.run(self.run())


def main(importer: BaseImporter) -> None:
    importer.execute()
