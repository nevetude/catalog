import sqlite3
import json


DB = "data/catalog.db"
OUTPUT = "keywords.txt"


conn = sqlite3.connect(DB)
cursor = conn.cursor()


cursor.execute(
    "SELECT keywords FROM movies"
)


keywords = set()


for (value,) in cursor.fetchall():

    if not value:
        continue

    for keyword in json.loads(value):
        keywords.add(keyword.strip())


conn.close()


with open(
    OUTPUT,
    "w",
    encoding="utf-8",
) as file:

    for keyword in sorted(keywords):
        file.write(
            f"{keyword}\n"
        )


print(
    f"Saved {len(keywords)} keywords"
)