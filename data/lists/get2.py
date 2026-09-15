import requests
from datetime import datetime
from pathlib import Path

BASE_URL = "https://files.tmdb.org/p/exports"
OUT_DIR = Path("tmdb_exports")

OUT_DIR.mkdir(exist_ok=True)

date = datetime.now().strftime("%m_%d_%Y")

files = [
    f"movie_ids_{date}.json.gz",
    f"tv_series_ids_{date}.json.gz",
    f"person_ids_{date}.json.gz",
    f"collection_ids_{date}.json.gz",
    f"tv_network_ids_{date}.json.gz",
    f"keyword_ids_{date}.json.gz",
    f"production_company_ids_{date}.json.gz",

    f"adult_movie_ids_{date}.json.gz",
    f"adult_tv_series_ids_{date}.json.gz",
    f"adult_person_ids_{date}.json.gz",
]

for filename in files:
    url = f"{BASE_URL}/{filename}"
    output = OUT_DIR / filename

    print(f"Downloading {filename}...")

    r = requests.get(url, stream=True)

    if r.status_code == 404:
        print("  Not available")
        continue

    r.raise_for_status()

    with open(output, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    print(f"  Saved: {output}")

print("Done.")