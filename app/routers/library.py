"""Library API: per-user folders and folder-scoped media listings."""

from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth import require_user
from app.db import get_db
from app.media import (
    MEDIA,
    MediaFilters,
    list_items,
    parse_media_filters,
    query_media,
    sort_items,
)

router = APIRouter(prefix="/api/library", tags=["library"])


def folder_slug(name: str) -> str:
    value = unicodedata.normalize("NFKC", str(name or "")).strip().lower()
    return re.sub(r"[^\w]+", "-", value, flags=re.UNICODE).strip("-_")


@router.get("/folders")
def list_folders(request: Request):
    user = require_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT f.id, f.name, f.created_at, "
            "(SELECT COUNT(*) FROM library_items i WHERE i.folder_id = f.id) AS item_count "
            "FROM library_folders f WHERE f.user_id = ? "
            "ORDER BY CASE f.name WHEN 'Watchlist' THEN 0 WHEN 'Watched' THEN 1 ELSE 2 END, "
            "f.name COLLATE NOCASE",
            (user["id"],),
        ).fetchall()
    return {"folders": [{**dict(r), "slug": folder_slug(r["name"])} for r in rows]}


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@router.post("/folders")
def create_folder(body: FolderCreate, request: Request):
    user = require_user(request)
    name = body.name.strip()
    slug = folder_slug(name)
    if not slug:
        raise HTTPException(400, "invalid folder name")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT name FROM library_folders WHERE user_id = ?", (user["id"],)
        ).fetchall()
        if any(folder_slug(r["name"]) == slug for r in rows):
            raise HTTPException(400, "folder exists")
        cursor = conn.execute(
            "INSERT INTO library_folders (user_id, name) VALUES (?, ?)", (user["id"], name)
        )
    return {"id": cursor.lastrowid, "name": name, "slug": slug}


@router.delete("/folders/{folder_id}")
def delete_folder(folder_id: int, request: Request):
    user = require_user(request)
    with get_db() as conn:
        conn.execute(
            "DELETE FROM library_folders WHERE id = ? AND user_id = ?", (folder_id, user["id"])
        )
    return {"ok": True}


@router.get("/membership")
def membership(
    request: Request,
    media_type: str = Query(pattern="^(movie|tv)$"),
    media_id: int = Query(ge=1),
):
    user = require_user(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT f.id, f.name FROM library_items i "
            "JOIN library_folders f ON f.id = i.folder_id "
            "WHERE f.user_id = ? AND i.media_type = ? AND i.media_id = ?",
            (user["id"], media_type, media_id),
        ).fetchall()
    names = {r["name"] for r in rows}
    return {
        "folder_ids": [r["id"] for r in rows],
        "in_watchlist": "Watchlist" in names,
        "in_watched": "Watched" in names,
        "in_library": bool(names),
    }


class ItemSync(BaseModel):
    media_type: str = Field(pattern="^(movie|tv)$")
    media_id: int = Field(ge=1)
    folder_ids: list[int] = Field(default_factory=list)


@router.post("/items")
def sync_item(body: ItemSync, request: Request):
    """Replace one media item's folder membership with the given folder ids."""
    user = require_user(request)
    folder_ids = list(dict.fromkeys(body.folder_ids))
    with get_db() as conn:
        owned = {
            r["id"]: r["name"]
            for r in conn.execute(
                "SELECT id, name FROM library_folders WHERE user_id = ?", (user["id"],)
            )
        }
        if set(folder_ids) - owned.keys():
            raise HTTPException(404, "folder not found")
        conn.execute(
            "DELETE FROM library_items WHERE media_type = ? AND media_id = ? "
            "AND folder_id IN (SELECT id FROM library_folders WHERE user_id = ?)",
            (body.media_type, body.media_id, user["id"]),
        )
        conn.executemany(
            "INSERT OR IGNORE INTO library_items (folder_id, media_type, media_id) "
            "VALUES (?, ?, ?)",
            [(fid, body.media_type, body.media_id) for fid in folder_ids],
        )
    names = {owned[fid] for fid in folder_ids}
    return {
        "ok": True,
        "folder_ids": folder_ids,
        "in_watchlist": "Watchlist" in names,
        "in_watched": "Watched" in names,
        "in_library": bool(names),
    }


@router.get("/folders/{folder_id}/items")
def folder_items(
    folder_id: int,
    request: Request,
    filters: MediaFilters = Depends(parse_media_filters),
    media_type: str = Query("all", pattern="^(movie|tv|all)$"),
    sort: str = "vote_count",
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    user = require_user(request)
    with get_db() as conn:
        folder = conn.execute(
            "SELECT id, name FROM library_folders WHERE id = ? AND user_id = ?",
            (folder_id, user["id"]),
        ).fetchone()
    if not folder:
        raise HTTPException(404, "folder not found")

    specs = list(MEDIA.values()) if media_type == "all" else [MEDIA[media_type]]
    items: list[dict] = []
    total = 0
    for spec in specs:
        scope = (
            ["id IN (SELECT media_id FROM library_items "
             "WHERE folder_id = ? AND media_type = ?)"],
            [folder_id, spec.key],
        )
        t, rows = query_media(spec, filters, scope=scope, sort=sort, order=order,
                              limit=offset + limit)
        total += t
        items += list_items(spec, rows, user["id"])
    items = sort_items(items, sort, order)[offset:offset + limit]
    return {
        "folder": {"id": folder["id"], "name": folder["name"], "slug": folder_slug(folder["name"])},
        "total": total,
        "items": items,
    }
