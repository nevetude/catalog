"""Import TV shows (with cast, episodes, images) from data/lists/shows.ndjson."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.import_base import (  # noqa: E402
    BaseImporter,
    TMDBClient,
    _keywords,
    flags,
    jdump,
    main,
    named_list,
    save_backdrops,
    us_tv_certification,
)


class ShowImporter(BaseImporter):
    media_type = "tv"
    list_file = "shows.ndjson"
    label = "shows"

    async def fetch(self, tmdb: TMDBClient, tmdb_id: int) -> dict | None:
        detail = await tmdb.get(f"/tv/{tmdb_id}", params={
            "language": "en-US",
            "append_to_response": "content_ratings,keywords,images",
            "include_image_language": "en,null",
        })
        if detail is None:
            return None
        # Episodes for every numbered season, fetched concurrently.
        seasons = [s["season_number"] for s in detail.get("seasons") or []
                   if (s.get("season_number") or 0) >= 1]
        pages = await asyncio.gather(
            *(tmdb.get(f"/tv/{tmdb_id}/season/{sn}") for sn in seasons)
        )
        detail["_episodes"] = [
            ep | {"_season": sn}
            for sn, page in zip(seasons, pages) if page
            for ep in page.get("episodes") or [] if ep.get("id")
        ]
        return detail

    def save(self, conn, data: dict, popularity: float | None) -> None:
        kw_names = _keywords(data)
        images = data.get("images") or {}
        show = {
            "id": data["id"],
            "type": data.get("type") or "Scripted",
            **flags(kw_names),
            "name": data.get("name") or data.get("original_name") or "",
            "original_name": data.get("original_name") or "",
            "status": data.get("status"),
            "in_production": data.get("in_production") or False,
            "adult": data.get("adult") or False,
            "certification": us_tv_certification(data),
            "first_air_date": data.get("first_air_date"),
            "last_air_date": data.get("last_air_date"),
            "episode_run_time": jdump(data.get("episode_run_time") or []),
            "number_of_seasons": data.get("number_of_seasons") or 0,
            "number_of_episodes": data.get("number_of_episodes") or 0,
            "origin_country": jdump(data.get("origin_country") or []),
            "original_language": data.get("original_language") or "",
            "languages": jdump(data.get("languages") or [
                s.get("iso_639_1") for s in data.get("spoken_languages") or [] if s.get("iso_639_1")
            ]),
            "spoken_languages": jdump(named_list(data.get("spoken_languages") or [],
                                                 "iso_639_1", "name", "english_name")),
            "genres": jdump([g["name"] for g in data.get("genres") or [] if g.get("name")]),
            "popularity": popularity if popularity is not None else data.get("popularity") or 0,
            "vote_average": data.get("vote_average") or 0,
            "vote_count": data.get("vote_count") or 0,
            "homepage": data.get("homepage"),
            "networks": jdump(named_list(data.get("networks") or [], "id", "name", "logo_path")),
            "production_countries": jdump(named_list(data.get("production_countries") or [],
                                                     "iso_3166_1", "name")),
            "production_companies": jdump(named_list(data.get("production_companies") or [],
                                                     "id", "name", "logo_path")),
            "poster_path": data.get("poster_path"),
            "backdrop_path": data.get("backdrop_path"),
            "tagline": data.get("tagline") or "",
            "overview": data.get("overview") or "",
            "seasons": jdump(named_list(data.get("seasons") or [],
                                        "id", "name", "season_number", "episode_count",
                                        "air_date", "overview", "poster_path")),
            "keywords": jdump(kw_names),
        }
        upsert(conn, show)
        save_backdrops(conn, self.media_type, data["id"], images.get("backdrops"))
        save_episodes(conn, data["id"], data["_episodes"])


def upsert(conn, show: dict) -> None:
    columns = ", ".join(show)
    placeholders = ", ".join(f":{c}" for c in show)
    updates = ", ".join(f"{c} = excluded.{c}" for c in show if c != "id")
    conn.execute(
        f"INSERT INTO shows ({columns}, updated_at) VALUES ({placeholders}, datetime('now')) "
        f"ON CONFLICT(id) DO UPDATE SET {updates}, updated_at = datetime('now')",
        show,
    )


def save_episodes(conn, show_id: int, episodes: list[dict]) -> None:
    conn.executemany(
        "INSERT INTO episodes (id, show_id, season_number, episode_number, name, overview, "
        "air_date, runtime, still_path, vote_average, vote_count) "
        "VALUES (:id, :show_id, :season_number, :episode_number, :name, :overview, :air_date, "
        ":runtime, :still_path, :vote_average, :vote_count) "
        "ON CONFLICT(id) DO UPDATE SET name = excluded.name, overview = excluded.overview, "
        "air_date = excluded.air_date, runtime = excluded.runtime, "
        "still_path = excluded.still_path, vote_average = excluded.vote_average, "
        "vote_count = excluded.vote_count",
        [
            {
                "id": ep["id"], "show_id": show_id,
                "season_number": ep["_season"],
                "episode_number": ep.get("episode_number") or 0,
                "name": ep.get("name"), "overview": ep.get("overview") or "",
                "air_date": ep.get("air_date"), "runtime": ep.get("runtime") or 0,
                "still_path": ep.get("still_path"),
                "vote_average": ep.get("vote_average") or 0,
                "vote_count": ep.get("vote_count") or 0,
            }
            for ep in episodes
        ],
    )


if __name__ == "__main__":
    main(ShowImporter())
