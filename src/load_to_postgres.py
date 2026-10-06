"""
load_to_postgres.py
Loads the five tables in data/processed/ into the boxes82 PostgreSQL database.
Run it after sql/create_tables.sql has created the empty tables.

Run from the project root:  python src/load_to_postgres.py
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

# Read the database settings from the .env file, so the password is never written in the code
load_dotenv(ROOT / ".env")
names = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
settings = {name: os.getenv(name) for name in names}  # a dictionary like {"DB_HOST": "localhost", ...}
missing = [name for name, value in settings.items() if not value]
if missing:
    raise SystemExit(f"Missing from .env: {missing}")

# URL.create builds the connection address safely, even if the password has symbols in it
url = URL.create(
    "postgresql+psycopg2",
    username=settings["DB_USER"],
    password=settings["DB_PASSWORD"],
    host=settings["DB_HOST"],
    port=int(settings["DB_PORT"]),
    database=settings["DB_NAME"],
)
engine = create_engine(url)

# Load order matters: tables that other tables point to (teams, players, games) go first
TABLES = ["teams", "players", "games", "player_game_stats", "shots"]
data = {name: pd.read_parquet(PROCESSED / f"{name}.parquet") for name in TABLES}

# engine.begin() starts one transaction: nothing is saved unless the whole block finishes,
# so a failure halfway through leaves the database empty instead of half loaded
with engine.begin() as conn:
    # Empty the tables first so running this twice doesn't double the data
    conn.execute(text("TRUNCATE shots, player_game_stats, games, players, teams"))

    for name in TABLES:
        # if_exists="append" adds rows to the table I already made in create_tables.sql
        # index=False so pandas doesn't try to add its own index column
        # chunksize=2000 sends the rows in batches (PostgreSQL limits how many values one statement can hold)
        data[name].to_sql(name, conn, if_exists="append", index=False, method="multi", chunksize=2000)
        print(f"loaded {name}: {len(data[name]):,} rows")

    # Count what is now in the database and compare with the files. If any count is
    # different, the assert fails and everything above is undone.
    for name in TABLES:
        in_db = conn.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar()
        assert in_db == len(data[name]), f"{name}: {in_db} in database vs {len(data[name])} in file"
        print(f"[PASS] {name}: {in_db:,} rows in database match the file")