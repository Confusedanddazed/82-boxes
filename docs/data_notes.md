# Data Exploration Notes


## test_nba_api.py

**Purpose:** Confirm Python can reach the NBA API and return accurate data before building the pipeline.

### Findings
- `teams.get_teams()` returns 30 teams (example: Lakers, id `1610612747`, abbreviation `LAL`). This can be the source for the `teams` table.
- `LeagueGameFinder`, filtered to the Lakers and the 2025-26 regular season, returned 82 games, so the full season is available.
- Manually checked the printed five games  against ESPN stats, they were accurate. 

### Takeaways
- The API connection works, and the data matches real results.
- Next step: look at all available columns to decide what to store.




## explore_columns.py 

**Purpose** Identify the available columns in the team and player game logs, check their data types and decide which to store.  

### Findings
- The team game log has 28 columns. 'PLUS_MINUS' will be used to verify the scores we derive.  
- The player game log (26,651 rows x 72 columns) for the 2025-26 season. About half of these columns are not needed. 
- 'GAME_ID' has leading zeros, so it is stored as 'VARCHAR(10)'.
'MATCHUP' shows home or away as text: 'BKN vs. NYK' is a home game, while 'BKN @ LAL' is an away game. 
- MIN is labeled as a NUMERIC(6,2) since it is stored as a decimal number (eg. 38.26333333)
- The two logs format dates slightly differently: '2026-04-12' in the team log, '2026-04-12T00:00:00' in the player log. 

### Missing Values
- Player log: Found 0 missing values across 26,651 rows x 18 columns. 
- Team log: Found 0 missing values across 2,460 rows x 7 columns. 

### Takeaways
- We have all the necessary data for point differential and Game Score. 
- Next step: update the ER diagram and set  up PostgreSQL. 

