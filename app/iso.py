"""ISO 3166-1 country and ISO 639-1 language maps loaded from app/data/iso."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ISO_DIR = Path(__file__).resolve().parent / "data" / "iso"


@lru_cache(maxsize=1)
def iso_maps() -> dict:
    """Code -> name maps for countries and languages; parsed once per process.

    Countries also carry the official name for tooltips.
    """
    countries = {
        code: {"name": entry["name"], "official": entry.get("officialName") or entry["name"]}
        for code, entry in json.loads(
            (ISO_DIR / "iso_3166-1.json").read_text(encoding="utf-8")
        ).items()
    }
    languages = {
        code: entry["name"]
        for code, entry in json.loads(
            (ISO_DIR / "iso_639-1.json").read_text(encoding="utf-8")
        ).items()
    }
    return {"countries": countries, "languages": languages}
