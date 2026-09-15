from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from app.config import (
    BACKDROP,
    BACKDROP_ORIG,
    CERT_ORDER,
    POSTER,
    STILL,
    STILL_EP,
)
from app.db import get_db

CHUNK = 500  # keep IN(...) lists well below SQLite's variable limit

# Earliest-dated film of its collection; `> ''` keeps empty-string dates out of MIN().
_FIRST_IN_COLLECTION = (
    "release_date = (SELECT MIN(m2.release_date) FROM movies m2 "
    "WHERE m2.belongs_to_collection = movies.belongs_to_collection "
    "AND m2.release_date > '')"
)


@dataclass(frozen=True)
class MediaSpec:
    key: str                 # public media type: "movie" or "tv"
    table: str
    title: str               # localized title column
    original: str            # original title column
    date: str                # release / first-air date column
    default_type: str        # fallback for the `type` column
    extra_sorts: frozenset[str]  # sort keys supported only by this table


MEDIA: dict[str, MediaSpec] = {
    "movie": MediaSpec(
        "movie", "movies", "title", "original_title", "release_date", "Movie",
        frozenset({"runtime", "budget", "revenue"}),
    ),
    "tv": MediaSpec(
        "tv", "shows", "name", "original_name", "first_air_date", "TV Series",
        frozenset({"episodes"}),
    ),
}


class MediaFilters(BaseModel):
    """Filter query parameters shared by every media listing endpoint (CSV where plural)."""

    q: Optional[str] = None
    status: Optional[str] = None
    statuses_exclude: Optional[str] = None
    type: Optional[str] = None
    collection: Optional[str] = None  # yes: in a collection, no: not in any
    first_in_collection: Optional[str] = None  # yes: first film of it, no: later sequel
    genres: Optional[str] = None
    companies: Optional[str] = None
    networks: Optional[str] = None
    min_score: Optional[float] = Field(None, ge=0, le=10)
    max_score: Optional[float] = Field(None, ge=0, le=10)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    episodes_from: Optional[int] = None
    episodes_to: Optional[int] = None
    runtime_from: Optional[int] = None
    runtime_to: Optional[int] = None
    languages: Optional[str] = None
    languages_exclude: Optional[str] = None
    countries: Optional[str] = None
    countries_exclude: Optional[str] = None
    certification: Optional[str] = None
    certifications_exclude: Optional[str] = None
    min_votes: Optional[int] = Field(None, ge=0)
    features: Optional[str] = None
    nsfw: Optional[str] = None
    min_budget: Optional[int] = Field(None, ge=0)
    max_budget: Optional[int] = Field(None, ge=0)

    def csv(self, name: str):
        return [
            x.strip()
            for x in (getattr(self,name) or "").split(",")
            if x.strip()
        ]


# --------------------------------------------------------------------------- SQL


def media_where(spec: MediaSpec, f: MediaFilters) -> tuple[list[str], list[Any]]:
    """Translate the shared filter model into a WHERE fragment for one table."""
    w: list[str] = []
    p: list[Any] = []

    if f.q:
        w.append(f"({spec.title} LIKE ? OR {spec.original} LIKE ?)")
        p += [f"%{f.q}%"] * 2

    if ins := f.csv("status"):
        w.append("(" + " OR ".join(["LOWER(status) = LOWER(?)"] * len(ins)) + ")")
        p += ins
    for s in f.csv("statuses_exclude"):
        w.append("(status IS NULL OR LOWER(status) != LOWER(?))")
        p.append(s)

    for attr, op in (("min_score", ">="), ("max_score", "<=")):
        if (v := getattr(f, attr)) is not None:
            w.append(f"vote_average {op} ?")
            p.append(v)
    if f.min_votes is not None:
        w.append("vote_count >= ?")
        p.append(f.min_votes)

    if f.year_from is not None:
        w.append(f"{spec.date} >= ?")
        p.append(f"{f.year_from:04d}-01-01")
    if f.year_to is not None:
        w.append(f"{spec.date} < ?")
        p.append(f"{f.year_to + 1:04d}-01-01")

    ranges = (
        (("episodes_from", "episodes_to"), "number_of_episodes", spec.key == "tv"),
        (("runtime_from", "runtime_to"), "runtime", spec.key == "movie"),
        (("min_budget", "max_budget"), "budget", spec.key == "movie"),
    )
    for (attr_from, attr_to), column, enabled in ranges:
        if not enabled:
            continue
        if (v := getattr(f, attr_from)) is not None:
            w.append(f"{column} >= ?")
            p.append(v)
        if (v := getattr(f, attr_to)) is not None:
            w.append(f"{column} <= ?")
            p.append(v)

    for lang in f.csv("languages"):
        w.append("LOWER(original_language) = LOWER(?)")
        p.append(lang)
    for lang in f.csv("languages_exclude"):
        w.append("(original_language IS NULL OR LOWER(original_language) != LOWER(?))")
        p.append(lang)
    for cc in f.csv("countries"):
        w.append("origin_country LIKE ?")
        p.append(f'%"{cc}"%')
    for cc in f.csv("countries_exclude"):
        w.append("(origin_country IS NULL OR origin_country NOT LIKE ?)")
        p.append(f'%"{cc}"%')
    if ins := f.csv("certification"):
        w.append("(" + " OR ".join(["UPPER(certification) = UPPER(?)"] * len(ins)) + ")")
        p += ins
    for cert in f.csv("certifications_exclude"):
        w.append("(certification IS NULL OR UPPER(certification) != UPPER(?))")
        p.append(cert)

    for t in f.csv("type"):
        w.append("LOWER(type) = LOWER(?)")
        p.append(t)
    # Tri-state Collection facet (movies only; the shows table has no collection column).
    if spec.key == "movie":
        for c in f.csv("collection"):
            if c.lower() == "yes":
                w.append("belongs_to_collection IS NOT NULL")
            elif c.lower() == "no":
                w.append("belongs_to_collection IS NULL")
        for v in f.csv("first_in_collection"):
            if v.lower() == "yes":
                w.append(_FIRST_IN_COLLECTION)
            elif v.lower() == "no":
                w.append(f"belongs_to_collection IS NOT NULL AND NOT ({_FIRST_IN_COLLECTION})")
    for g in f.csv("genres"):
        w.append("genres LIKE ?")
        p.append(f'%"{g}"%')
    for cid in f.csv("companies"):
        w.append("production_companies LIKE ?")
        p.append(f'%"id": {cid},%')
    if spec.key == "tv":
        for nid in f.csv("networks"):
            w.append("networks LIKE ?")
            p.append(f'%"id": {nid},%')

    features = {x.lower() for x in f.csv("features")}

    # Content: boolean flag columns filled by the importers from TMDB keywords.
    # 'short' maps to the dedicated type column (importer classification).
    for flag in ("anime", "donghua", "aeni", "amerime"):
        if flag in features:
            w.append(f"{flag} = 1")
    if "short" in features:
        w.append("type = 'Short'")
    if "tv_movie" in features:
        w.append("type = 'TV Movie'")

    nsfw = {x.lower() for x in f.csv("nsfw")}
    for flag in ("adult", "softcore", "gay", "lesbian"):
        if flag in nsfw:
            w.append(f"{flag} = 1")

    return w, p


_SORT_COLUMNS = {
    "runtime": "runtime",
    "budget": "budget",
    "revenue": "revenue",
    "episodes": "number_of_episodes",
}
_BASE_SORTS = {"popularity", "vote_average", "vote_count"}


def order_sql(spec: MediaSpec, sort: str, order: str) -> str:
    if sort == "name":
        column = f"{spec.title} COLLATE NOCASE"
    elif sort in ("year", "release_date", "first_air_date"):
        column = spec.date
    elif sort in _BASE_SORTS or sort in _SORT_COLUMNS and sort in spec.extra_sorts:
        column = _SORT_COLUMNS.get(sort, sort)
    else:
        column = "vote_count"
    return f"{column} {'DESC' if order == 'desc' else 'ASC'}"


def query_media(
    spec: MediaSpec,
    filters: MediaFilters,
    *,
    scope: tuple[list[str], list[Any]] = ((), []),
    sort: str = "vote_count",
    order: str = "desc",
    limit: int = 500,
    offset: int = 0,
) -> tuple[int, list]:
    """Filtered, sorted, paginated rows. `scope` adds extra WHERE conditions (ACL-style)."""
    where, params = media_where(spec, filters)
    where += scope[0]
    params += scope[1]
    where_sql = " AND ".join(where) or "1=1"
    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM {spec.table} WHERE {where_sql}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM {spec.table} WHERE {where_sql} "
            f"ORDER BY {order_sql(spec, sort, order)} LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    return total, rows


_SORT_KEYS = {
    "name": lambda i: (i["title"] or "").lower(),
    "vote_average": lambda i: i["vote_average"] or 0,
    "popularity": lambda i: i["popularity"] or 0,
    "vote_count": lambda i: i["vote_count"] or 0,
    "year": lambda i: int(i["year"] or 0),
    "release_date": lambda i: int(i["year"] or 0),
    "first_air_date": lambda i: int(i["year"] or 0),
    "runtime": lambda i: i["runtime"] or 0,
    "budget": lambda i: i["budget"] or 0,
    "revenue": lambda i: i["revenue"] or 0,
    "episodes": lambda i: i["episodes"] or 0,
}


def sort_items(items: list[dict], sort: str, order: str) -> list[dict]:
    key = _SORT_KEYS.get(sort, _SORT_KEYS["vote_count"])
    return sorted(items, key=key, reverse=order == "desc")


# ----------------------------------------------------------------------- cards


def jload(value: Any, default: Any = None) -> Any:
    if default is None:
        default = []
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def card(spec: MediaSpec, row) -> dict:
    """Card payload shared by every listing endpoint."""
    item = {
        "id": row["id"],
        "media_type": spec.key,
        "type": row["type"] or spec.default_type,
        "title": row[spec.title] or row[spec.original],
        "original_title": row[spec.original],
        "poster": POSTER + row["poster_path"] if row["poster_path"] else None,
        "popularity": round(row["popularity"] or 0, 2),
        "vote_average": round(row["vote_average"] or 0, 1),
        "vote_count": row["vote_count"] or 0,
        "year": (row[spec.date] or "")[:4] or None,
        "status": row["status"],
        "certification": row["certification"],
        "adult": bool(row["adult"]),
        "softcore": bool(row["softcore"]),
        "genres": jload(row["genres"]),
        "origin_country": jload(row["origin_country"]),
        "original_language": row["original_language"] or "",
        "runtime": None,
        "budget": None,
        "revenue": None,
        "episodes": None,
        "seasons": None,
        "in_watchlist": False,
        "in_watched": False,
        "in_library": False,
    }
    if spec.key == "movie":
        item.update(runtime=row["runtime"] or 0, budget=row["budget"] or 0,
                    revenue=row["revenue"] or 0)
    else:
        item.update(episodes=row["number_of_episodes"] or 0,
                    seasons=row["number_of_seasons"] or 0)
    return item



def attach_library_flags(items: list[dict], user_id: Optional[int]) -> None:
    if not user_id or not items:
        return
    ids_by_type: dict[str, list[int]] = {}
    for item in items:
        ids_by_type.setdefault(item["media_type"], []).append(item["id"])
    folders: dict[tuple[str, int], set[str]] = {}
    with get_db() as conn:
        for mt, ids in ids_by_type.items():
            for start in range(0, len(ids), CHUNK):
                chunk = ids[start:start + CHUNK]
                rows = conn.execute(
                    f"SELECT i.media_type, i.media_id, f.name FROM library_items i "
                    f"JOIN library_folders f ON f.id = i.folder_id "
                    f"WHERE f.user_id = ? AND i.media_type = ? "
                    f"AND i.media_id IN ({','.join('?' * len(chunk))})",
                    (user_id, mt, *chunk),
                ).fetchall()
                for r in rows:
                    folders.setdefault((r["media_type"], r["media_id"]), set()).add(r["name"])
    for item in items:
        names = folders.get((item["media_type"], item["id"]), set())
        item["in_watchlist"] = "Watchlist" in names
        item["in_watched"] = "Watched" in names
        item["in_library"] = bool(names)


def list_items(spec: MediaSpec, rows: list, user_id: Optional[int]) -> list[dict]:
    """Cards with library flags — shared by every listing endpoint."""
    items = [card(spec, r) for r in rows]
    attach_library_flags(items, user_id)
    return items


# ---------------------------------------------------------------------- details


def load_stills(spec: MediaSpec, media_id: int, fallback_path: str | None) -> list[dict]:
    """Backdrops of one title: w780 previews + originals for the lightbox."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT file_path FROM backdrops WHERE media_type = ? AND media_id = ? "
            "ORDER BY id",
            (spec.key, media_id),
        ).fetchall()
    paths = [r["file_path"] for r in rows if r["file_path"]]
    if not paths and fallback_path:
        paths = [fallback_path]
    return [{"thumb": STILL + p, "full": BACKDROP_ORIG + p} for p in paths]


def _season_data(show_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM episodes WHERE show_id = ? ORDER BY season_number, episode_number",
            (show_id,),
        ).fetchall()
    seasons: dict[int, list[dict]] = {}
    for e in rows:
        seasons.setdefault(e["season_number"], []).append({
            "id": e["id"],
            "season": e["season_number"],
            "episode": e["episode_number"],
            "name": e["name"] or f"Episode {e['episode_number']}",
            "overview": e["overview"] or "",
            "air_date": e["air_date"],
            "runtime": e["runtime"] or 0,
            "still": STILL_EP + e["still_path"] if e["still_path"] else None,
            "vote_average": round(e["vote_average"] or 0, 1),
        })
    return [{"season_number": sn, "episodes": eps} for sn, eps in sorted(seasons.items())]


def detail(spec: MediaSpec, row) -> dict:
    data = card(spec, row)
    if row["poster_path"]:
        data["poster"] = POSTER + row["poster_path"]
    data.update(
        backdrop=BACKDROP + row["backdrop_path"] if row["backdrop_path"] else None,
        homepage=row["homepage"],
        overview=row["overview"] or "",
        tagline=row["tagline"] or "",
        keywords=jload(row["keywords"]),
        production_companies=jload(row["production_companies"]),
        production_countries=jload(row["production_countries"]),
        spoken_languages=jload(row["spoken_languages"]),
        languages=jload(row["languages"]),
        stills=load_stills(spec, row["id"], row["backdrop_path"]),
    )
    if spec.key == "movie":
        data.update(release_date=row["release_date"], imdb_id=row["imdb_id"], collection=None)
        if row["belongs_to_collection"]:
            data["collection"] = {
                "id": row["belongs_to_collection"],
                "name": row["collection_name"],
                "poster": None,
            }
    else:
        data.update(
            first_air_date=row["first_air_date"],
            last_air_date=row["last_air_date"],
            in_production=bool(row["in_production"]),
            networks=jload(row["networks"]),
            episode_run_time=jload(row["episode_run_time"]),
            seasons_meta=jload(row["seasons"]),
            seasons_data=_season_data(row["id"]),
        )
    return data


# ------------------------------------------------------------------- options


def _sorted_certs(certs: set[str]) -> list[str]:
    rank = {c: i for i, c in enumerate(CERT_ORDER)}
    return sorted(certs, key=lambda c: (rank.get(c, 999), c))


def _collect_options(spec: MediaSpec, where: list[str], params: list) -> dict:
    """Distinct filter values and numeric ranges for one table under an optional scope."""
    where_sql = " AND ".join(where) or "1=1"
    cols = ("certification, original_language, status, origin_country, "
            "type, genres, production_companies, "
            "adult, softcore, gay, lesbian, anime, donghua, aeni, amerime")
    if spec.key == "tv":
        cols += ", networks"
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT {cols} FROM {spec.table} WHERE {where_sql}", params,
        ).fetchall()
        # `> ''` keeps empty-string dates (importer artifact) out of the year bounds
        dates = conn.execute(
            f"SELECT MIN({spec.date}), MAX({spec.date}) FROM {spec.table} "
            f"WHERE {spec.date} > '' AND ({where_sql})",
            params,
        ).fetchone()
        extra: dict[str, Any] = {"runtime_min": 0, "runtime_max": 0,
                                 "budget_min": 0, "budget_max": 0,
                                 "episodes_min": 0, "episodes_max": 0}
        if spec.key == "movie":
            low, high, low_b, high_b = conn.execute(
                f"SELECT MIN(runtime), MAX(runtime), MIN(budget), MAX(budget) "
                f"FROM {spec.table} WHERE runtime > 0 AND ({where_sql})", params,
            ).fetchone()
            extra.update(runtime_min=low or 0, runtime_max=high or 300,
                         budget_min=low_b or 0, budget_max=high_b or 500_000_000)
        else:
            low, high = conn.execute(
                f"SELECT MIN(number_of_episodes), MAX(number_of_episodes) "
                f"FROM {spec.table} WHERE number_of_episodes > 0 AND ({where_sql})", params,
            ).fetchone()
            extra.update(episodes_min=low or 0, episodes_max=high or 100)

    certs: dict[str, int] = {}
    langs: dict[str, int] = {}
    statuses: dict[str, int] = {}
    countries: dict[str, int] = {}
    years: set[int] = set()
    types: dict[str, int] = {}
    genres: dict[str, int] = {}
    companies: dict[int, dict] = {}
    networks: dict[int, dict] = {}
    flags = {k: 0 for k in ("short", "tv_movie", "anime", "donghua", "aeni",
                            "amerime", "adult", "softcore", "gay", "lesbian")}
    for r in rows:
        if r["certification"]:
            certs[r["certification"]] = certs.get(r["certification"], 0) + 1
        if r["original_language"]:
            code = r["original_language"].strip().lower()
            langs[code] = langs.get(code, 0) + 1
        if r["status"]:
            statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        for c in jload(r["origin_country"]):
            if c:
                code = str(c).strip().upper()
                countries[code] = countries.get(code, 0) + 1
        if r["type"]:
            types[r["type"]] = types.get(r["type"], 0) + 1
        if r["type"] == "Short":
            flags["short"] += 1
        if r["type"] == "TV Movie":
            flags["tv_movie"] += 1
        for g in jload(r["genres"]):
            if g:
                genres[g] = genres.get(g, 0) + 1
        for flag in ("adult", "softcore", "gay", "lesbian",
                     "anime", "donghua", "aeni", "amerime"):
            if r[flag]:
                flags[flag] += 1
        for entity, bucket in (("production_companies", companies), ("networks", networks)):
            if entity not in r.keys():
                continue
            for item in jload(r[entity]):
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                entry = bucket.setdefault(item["id"], {
                    "id": item["id"], "name": item.get("name") or "",
                    "logo": item.get("logo_path"), "count": 0,
                })
                entry["count"] += 1
    for value in dates:
        if value and str(value)[:4].isdigit():
            years.add(int(str(value)[:4]))

    def top(bucket: dict) -> list:
        return sorted(bucket.values(), key=lambda x: -x["count"])[:200]

    return {
        "certifications": set(certs),
        "certification_counts": certs,
        "languages": set(langs),
        "language_counts": langs,
        "statuses": set(statuses),
        "status_counts": statuses,
        "countries": set(countries),
        "country_counts": countries,
        "years": years,
        "types": set(types),
        "type_counts": types,
        "genres": set(genres),
        "genre_counts": genres,
        "companies": top(companies),
        "networks": top(networks),
        "flag_counts": flags,
        **extra,
    }


_OPTIONS_CACHE: dict[str, tuple[int, dict]] = {}


def _finalize_options(raw: dict) -> dict:
    """Keep the raw value sets and add year bounds derived from them."""
    raw.setdefault("years", set())
    years = raw["years"]
    raw["year_min"] = min(years) if years else 1900
    raw["year_max"] = max(years) if years else 2030
    return raw


def _serialize_options(raw: dict) -> dict:
    """Sets -> sorted lists so the payload is JSON-ready; *_counts pass through."""
    raw["certifications"] = _sorted_certs(set(raw.get("certifications", set())))
    for key in _SET_KEYS:
        if key != "certifications":
            raw[key] = sorted(raw.get(key, set()) or set())
    for key in _COUNT_KEYS:
        raw[key] = raw.get(key, {})
    return raw


def filter_options(spec: MediaSpec, scope: tuple[list[str], list] | None = None) -> dict:
    """Filter options for one table; the unscoped variant is cached by DB data version."""
    with get_db() as conn:
        version = conn.execute("PRAGMA data_version").fetchone()[0]
    if scope is None:
        cached = _OPTIONS_CACHE.get(spec.key)
        if cached and cached[0] == version:
            return cached[1]
    result = _serialize_options(_finalize_options(
        _collect_options(spec, *scope) if scope else _collect_options(spec, [], [])
    ))
    if scope is None:
        _OPTIONS_CACHE[spec.key] = (version, result)
    return result


_SET_KEYS = ("certifications", "languages", "statuses", "countries", "years", "types", "genres")
_COUNT_KEYS = ("certification_counts", "language_counts", "status_counts",
               "country_counts", "type_counts", "genre_counts", "flag_counts")
_BOUNDS = {"year_min": 1900, "year_max": 2030, "runtime_min": 0, "runtime_max": 300,
           "episodes_min": 0, "episodes_max": 100, "budget_min": 0, "budget_max": 500_000_000}


def merge_options(options: list[dict]) -> dict:
    """Union of per-table option sets: sum counts, merge entities, span bounds."""
    if not options:
        options = [{}]
    merged: dict = {}
    for key in _SET_KEYS:
        merged[key] = set().union(*(o.get(key, set()) for o in options))
    for key in _COUNT_KEYS:
        counts: dict = {}
        for o in options:
            for code, n in (o.get(key) or {}).items():
                counts[code] = counts.get(code, 0) + n
        merged[key] = counts
    for key in ("companies", "networks"):
        by_id: dict[int, dict] = {}
        for o in options:
            for c in o.get(key, []):
                if isinstance(c, dict) and c.get("id"):
                    by_id[c["id"]] = c
        merged[key] = sorted(by_id.values(), key=lambda x: -x.get("count", 0))[:200]
    for key, default in _BOUNDS.items():
        values = [o[key] for o in options if o.get(key)]
        merged[key] = (min if key.endswith("_min") else max)(values) if values else default
    return _serialize_options(_finalize_options(merged))


def parse_media_filters(request: Request) -> MediaFilters:
    """Build the shared filter model from raw query params (FastAPI-version-proof)."""
    try:
        return MediaFilters.model_validate(dict(request.query_params))
    except ValidationError as error:
        first = error.errors()[0]
        field = ".".join(str(part) for part in first.get("loc", ()))
        raise HTTPException(422, f"invalid filter '{field}': {first.get('msg')}") from error
