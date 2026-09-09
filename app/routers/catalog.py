"""Catalog API: listings, filter values, media details, persons, companies, collections."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth import current_user
from app.config import PROFILE
from app.db import get_db
from app.iso import iso_maps
from app.media import (
    MEDIA,
    MediaFilters,
    MediaSpec,
    attach_library_flags,
    detail,
    filter_options,
    jload,
    list_items,
    merge_options,
    parse_media_filters,
    query_media,
    sort_items,
)

router = APIRouter(prefix="/api", tags=["catalog"])


def _uid(request: Request) -> Optional[int]:
    user = current_user(request)
    return user and user["id"]


@router.get("/catalog")
def catalog(
    request: Request,
    filters: MediaFilters = Depends(parse_media_filters),
    media_type: str = Query("movie", pattern="^(movie|tv)$"),
    sort: str = "vote_count",
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    spec = MEDIA[media_type]
    total, rows = query_media(spec, filters, sort=sort, order=order, limit=limit, offset=offset)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "media_type": media_type,
        "items": list_items(spec, rows, _uid(request)),
    }


@router.get("/filters")
def filter_values(media_type: str = Query("movie", pattern="^(movie|tv)$")):
    return filter_options(MEDIA[media_type])


@router.get("/iso")
def iso():
    """ISO 3166-1 / ISO 639-1 code -> name maps (app/data/iso/*.json)."""
    return iso_maps()


def _detail_or_404(request: Request, spec: MediaSpec, media_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute(f"SELECT * FROM {spec.table} WHERE id = ?", (media_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"{spec.key} not found")
    data = detail(spec, row)
    attach_library_flags([data], _uid(request))
    return data


@router.get("/movie/{movie_id}")
def movie_detail(movie_id: int, request: Request):
    return _detail_or_404(request, MEDIA["movie"], movie_id)


@router.get("/show/{show_id}")
def show_detail(show_id: int, request: Request):
    return _detail_or_404(request, MEDIA["tv"], show_id)


@router.get("/collection/{collection_id}")
def collection_detail(
    request: Request,
    collection_id: int,
    filters: MediaFilters = Depends(parse_media_filters),
    sort: str = "year",
    order: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    spec = MEDIA["movie"]
    scope = (["belongs_to_collection = ?"], [collection_id])
    with get_db() as conn:
        head = conn.execute(
            "SELECT collection_name FROM movies WHERE belongs_to_collection = ? LIMIT 1",
            (collection_id,),
        ).fetchone()
    if not head:
        raise HTTPException(404, "collection not found")
    total, rows = query_media(spec, filters, scope=scope, sort=sort, order=order,
                              limit=limit, offset=offset)
    return {
        "collection": {"id": collection_id, "name": head["collection_name"], "poster": None},
        "total": total,
        "items": list_items(spec, rows, _uid(request)),
    }


@router.get("/person/{person_id}")
def person_detail(
    person_id: int,
    request: Request,
    filters: MediaFilters = Depends(parse_media_filters),
    media_kind: Optional[str] = Query(None, pattern="^(movie|tv|feature|short)$"),
    role: Optional[str] = None,
    sort: str = "year",
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    with get_db() as conn:
        person = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
        if not person:
            raise HTTPException(404, "person not found")
        credit_rows = conn.execute(
            "SELECT media_type, media_id, job FROM credits WHERE person_id = ?",
            (person_id,),
        ).fetchall()

    # Jobs per media record; credits store the media type in either case (legacy rows).
    roles_by_media: dict[tuple[str, int], list[str]] = {}
    for c in credit_rows:
        mt = c["media_type"].strip().lower()
        if mt in MEDIA:
            roles_by_media.setdefault((mt, c["media_id"]), []).append(c["job"])

    specs = list(MEDIA.values())
    type_clause = ""
    if media_kind in ("feature", "short"):
        specs = [MEDIA["movie"]]
        type_clause = "type != 'Short'" if media_kind == "feature" else "type = 'Short'"
    elif media_kind in MEDIA:
        specs = [MEDIA[media_kind]]

    items: list[dict] = []
    options: list[dict] = []
    total = 0
    user_id = _uid(request)
    for spec in specs:
        scope = [
            f"EXISTS (SELECT 1 FROM credits pc WHERE pc.person_id = ? "
            f"AND pc.media_id = {spec.table}.id AND LOWER(pc.media_type) = ?)"
        ]
        params: list[Any] = [person_id, spec.key]
        if role:
            scope.append(
                f"EXISTS (SELECT 1 FROM credits rc WHERE rc.person_id = ? "
                f"AND rc.media_id = {spec.table}.id AND rc.job = ?)"
            )
            params += [person_id, role]
        if type_clause:
            scope.append(type_clause)
        t, rows = query_media(spec, filters, scope=(scope, params), sort=sort, order=order,
                              limit=offset + limit)
        total += t
        items += list_items(spec, rows, user_id)
        options.append(filter_options(spec, scope=(scope, params)))
        for item, row in zip(items[-len(rows):], rows):
            jobs = list(dict.fromkeys(roles_by_media.get((spec.key, row["id"]), [])))
            item["role"] = ", ".join(jobs)
            item["roles"] = jobs

    items = sort_items(items, sort, order)[offset:offset + limit]
    return {
        "person": {
            "id": person["id"],
            "name": person["name"],
            "profile": (PROFILE + person["profile_path"]) if person["profile_path"] else None,
            "biography": person["biography"] or "",
            "birthday": person["birthday"],
            "place_of_birth": person["place_of_birth"],
            "known_for_department": person["known_for_department"],
        },
        "roles": sorted({job for jobs in roles_by_media.values() for job in jobs}),
        "filter_options": merge_options(options),
        "total": total,
        "items": items,
    }


@router.get("/company/{company_id}")
def company_detail(
    company_id: int,
    request: Request,
    filters: MediaFilters = Depends(parse_media_filters),
    media_type: str = Query("all", pattern="^(movie|tv|all)$"),
    sort: str = "vote_count",
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    # production_companies JSON is written by the importers as {"id": N, "name": ...};
    # the quoted-key prefix makes the LIKE match exact ids only (3 does not match 30).
    scope = (["production_companies LIKE ?"], [f'%"id": {company_id},%'])
    specs = list(MEDIA.values()) if media_type == "all" else [MEDIA[media_type]]

    with get_db() as conn:
        company = None
        for spec in specs:
            row = conn.execute(
                f"SELECT production_companies FROM {spec.table} "
                f"WHERE production_companies LIKE ? LIMIT 1",
                scope[1],
            ).fetchone()
            if row:
                company = next(
                    (c for c in jload(row[0]) if c.get("id") == company_id), company
                )
    if company is None:
        raise HTTPException(404, "company not found")

    items: list[dict] = []
    options: list[dict] = []
    total = 0
    user_id = _uid(request)
    for spec in specs:
        t, rows = query_media(spec, filters, scope=scope, sort=sort, order=order,
                              limit=offset + limit)
        total += t
        items += list_items(spec, rows, user_id)
        options.append(filter_options(spec, scope=scope))
    items = sort_items(items, sort, order)[offset:offset + limit]
    return {
        "company": company,
        "filter_options": merge_options(options),
        "total": total,
        "items": items,
    }
