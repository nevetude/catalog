"""Import movies (with cast, images) from data/lists/movies.ndjson."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.import_base import (
    BaseImporter,
    TMDBClient,
    _keywords,
    flags,
    jdump,
    main,
    named_list,
    save_backdrops,
    us_certification,
)


class MovieImporter(BaseImporter):
    media_type = "movie"
    list_file = "movies.ndjson"
    label = "movies"

    async def fetch(self, tmdb: TMDBClient, tmdb_id: int) -> dict | None:
        return await tmdb.get(f"/movie/{tmdb_id}", params={
            "language": "en-US",
            "append_to_response": "release_dates,keywords,images",
            "include_image_language": "en,null",
        })

    def save(self, conn, data: dict, popularity: float | None) -> None:
        kw_names = _keywords(data)
        genre_names = [g["name"] for g in data.get("genres") or [] if g.get("name")]
        collection = data.get("belongs_to_collection") or {}
        movie = {
            "id": data["id"],
            "type": ("Short" if any(k.strip().lower() == "short film" for k in kw_names)
                     else "TV Movie" if "TV Movie" in genre_names
                     else "Movie"),
            **flags(kw_names),
            "title": data.get("title") or "",
            "original_title": data.get("original_title") or "",
            "status": data.get("status"),
            "adult": data.get("adult") or False,
            "certification": us_certification(data),
            "popularity": popularity if popularity is not None else data.get("popularity") or 0,
            "overview": data.get("overview") or "",
            "poster_path": data.get("poster_path"),
            "backdrop_path": data.get("backdrop_path"),
            "release_date": data.get("release_date"),
            "runtime": data.get("runtime") or 0,
            "vote_average": data.get("vote_average") or 0,
            "vote_count": data.get("vote_count") or 0,
            "genres": jdump(genre_names),
            "origin_country": jdump(
                data.get("origin_country")
                or [c["iso_3166_1"] for c in data.get("production_countries") or []
                    if c.get("iso_3166_1")]
            ),
            "original_language": data.get("original_language") or "",
            "languages": jdump([lang["iso_639_1"] for lang in data.get("spoken_languages") or []
                             if lang.get("iso_639_1")]),
            "spoken_languages": jdump(named_list(data.get("spoken_languages") or [],
                                                 "iso_639_1", "name", "english_name")),
            "budget": data.get("budget") or 0,
            "revenue": data.get("revenue") or 0,
            "tagline": data.get("tagline") or "",
            "imdb_id": data.get("imdb_id"),
            "homepage": data.get("homepage"),
            "belongs_to_collection": collection.get("id"),
            "collection_name": collection.get("name"),
            "production_companies": jdump(named_list(data.get("production_companies") or [],
                                                     "id", "name", "logo_path")),
            "production_countries": jdump(named_list(data.get("production_countries") or [],
                                                     "iso_3166_1", "name")),
            "keywords": jdump(kw_names),
        }
        upsert(conn, movie)
        backdrops = (data.get("images") or {}).get("backdrops")
        save_backdrops(conn, self.media_type, data["id"], backdrops)


def upsert(conn, movie: dict) -> None:
    columns = ", ".join(movie)
    placeholders = ", ".join(f":{c}" for c in movie)
    updates = ", ".join(f"{c} = excluded.{c}" for c in movie if c != "id")
    conn.execute(
        f"INSERT INTO movies ({columns}, updated_at) VALUES ({placeholders}, datetime('now')) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}, updated_at = datetime('now')",
        movie,
    )


if __name__ == "__main__":
    main(MovieImporter())
