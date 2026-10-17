"""
load_to_postgres.py
Loads the cleaned data files into the boxes82 PostgreSQL database.
Run it after sql/create_tables.sql has created the empty tables.
 
Run from the project root:  python src/load_to_postgres.py
"""
import os
from pathlib import Path
 
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
 
# Folders
ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
 
# 1. Read the database settings from the .env file.
#    The password lives in .env so it is never written in the code or put on GitHub.
load_dotenv(ROOT / ".env")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
name = os.getenv("DB_NAME")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
 
if not all([host, port, name, user, password]):
    raise SystemExit("Something is missing in .env. Check all five DB_ settings.")
 
# 2. Connect to the database.
#    URL.create builds the address for us, even if the password has symbols in it.
url = URL.create(
    "postgresql+psycopg2",
    username=user,
    password=password,
    host=host,
    port=int(port),
    database=name,
)
engine = create_engine(url)
 
# 3. Read the cleaned files into memory.
# The order matters: teams, players and games go first because the other tables refer to them.
tables = ["teams", "players", "games", "player_game_stats", "shots"]
data = {}
for table in tables:
    data[table] = pd.read_parquet(PROCESSED / f"{table}.parquet")
 
# 4. Load everything inside one "transaction".
#    A transaction means all-or-nothing: if anything fails, every change is undone,
#    so the database is never left half loaded.
with engine.begin() as conn:
 
    # Empty the tables first so running this script twice doesn't double the data.
    conn.execute(text("TRUNCATE shots, player_game_stats, games, players, teams"))
 
    # Add each file's rows to the table made by create_tables.sql.
    for table in tables:
        data[table].to_sql(
            table,
            conn,
            if_exists="append",
            index=False,           
            method="multi",        # insert many rows per command (faster)
            chunksize=2000,        # 2000 rows being sent at a time
        )
        print(f"loaded {table}: {len(data[table]):,} rows")
 
    # 5. Check: count the rows now in the database and compare with the files.
    #    If a count is different, we stop here and the whole load is undone.
    for table in tables:
        rows_in_db = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        rows_in_file = len(data[table])
        if rows_in_db != rows_in_file:
            raise SystemExit(f"{table}: {rows_in_db} rows in database, {rows_in_file} in file")
        print(f"[PASS] {table}: {rows_in_db:,} rows match the file")
 