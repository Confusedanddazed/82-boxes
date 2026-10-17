# head 2 head

head 2 head is an end-to-end interactive NBA dashboard that compares two players across the 2025-26 season.

## Examples

### Dylan Harper vs VJ Edgecombe

![Dylan Harper vs VJ Edgecombe](assets/harper_vs_edgecombe.jpg)

I compared the second and third picks from the 2025 draft class. Since they are rookies, their heatmaps and stats usually show more volatility. At a glance, VJ appears to have had the better season. However, because he played 12 more minutes per game, his counting stats are expected to be higher. From a Game Score standpoint, VJ still has the edge: he had 13 games above the 90th percentile, while Dylan only had 4. 

## Features

- Python script that pulls the 2025-26 season from the NBA API, with credentials kept in a `.env` file 
- 26 automatic data checks before anything is saved, plus manual comparison against ESPN 
- Five-table PostgreSQL database, loaded in one all-or-nothing step with row counts checked against the source files (schema in docs/erd)
- SQL views (CTEs, joins and window functions) that calculate team scores, standings, Game Score and its percentile
- Two player slicers that update every visual, with player cards, delta arrows and league ranks
- 82-game heatmaps based on league-wide Game Score percentiles
- Shot charts of every field goal attempt, drawn on the home team's court
- 10-game rolling average for any stat chosen in the stat picker

## Technologies

- NBA data API (`nba_api`)
- Python
- PostgreSQL
- SQL
- PowerBI (DAX, Deneb, JSON)

## Instructions to run

You need Python 3.10+, PostgreSQL and Power BI Desktop.

1. Download or clone this repository.
2. Create an empty PostgreSQL database named boxes82.
3. Install the packages: pip install nba_api pandas pyarrow SQLAlchemy psycopg2-binary python-dotenv
4. Copy .env.example to .env and fill in your database settings.
5. Run the scripts in order:
        python src/extract_data.py
        python src/clean_data.py
        psql -d boxes82 -f sql/create_tables.sql
        python src/load_to_postgres.py
        psql -d boxes82 -f sql/views.sql
6. Open powerbi/head2head.pbix, point its data source at your database and click Refresh.



