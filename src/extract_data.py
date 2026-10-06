"""
extract_data.py
Pull the 2025-26 regular season from the NBA API and save it UNTOUCHED to data/raw/.
Data cleaning will be done in clean_data.py.

Run from the project root:  python src/extract_data.py

"""
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder, playergamelogs, shotchartdetail

SEASON = "2025-26"
SEASON_TYPE = "Regular Season"

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 1. Team game log: one row per team per game
team_log = leaguegamefinder.LeagueGameFinder(
    season_nullable=SEASON,
    season_type_nullable=SEASON_TYPE,
    timeout=60,
).get_data_frames()[0]
print("team_log:", team_log.shape) # expect 2460(82 games x 30 teams)

# Verify the team log is complete: all 30 teams, 82 games each
assert team_log["TEAM_ID"].nunique() == 30, "Team log is missing teams"
assert team_log.groupby("TEAM_ID").size().eq(82).all(), "A team doesn't have 82 games"
print("team_log OK: 30 teams x 82 games")

# 2. Player game log: one row per player per game they appeared in
player_log = playergamelogs.PlayerGameLogs(
    season_nullable=SEASON,
    season_type_nullable=SEASON_TYPE,
    timeout=60,
).get_data_frames()[0]
print("player_log:", player_log.shape) # expect 26,651

# Verify the player log is complete: every game is present and no player-game row is duplicated
assert not player_log.duplicated(["GAME_ID", "PLAYER_ID"]).any(), "Duplicate player-game rows"
assert player_log["GAME_ID"].nunique() == 1230, "Player log is missing games"
print("player_log OK: 1,230 games, no duplicate player-game rows")

# 3. Shot chart: one call per team, since a single league-wide call is capped
#    at 102,400. Loop through each team ID, collect each team's shots in all_shot_charts 
#    and cancat them into one table. 
all_shot_charts = []
for team_id in team_log["TEAM_ID"].unique():
    shots_for_team = shotchartdetail.ShotChartDetail(
        team_id=int(team_id),
        player_id=0,
        context_measure_simple="FGA",
        season_nullable=SEASON,
        season_type_all_star=SEASON_TYPE,
        timeout=180,
    ).get_data_frames()[0]
    all_shot_charts.append(shots_for_team)
    print(f"  shots for team {team_id}: {len(shots_for_team)} rows")
    time.sleep(1)
shot_chart = pd.concat(all_shot_charts, ignore_index=True)
print("shot_chart:", shot_chart.shape)

# Confirm every team and game was collected
teams_collected = shot_chart["TEAM_ID"].nunique()
games_collected = shot_chart["GAME_ID"].nunique()
print(f"Collected shot charts for {teams_collected} of 30 teams and {games_collected} of 1,230 games")
assert teams_collected == 30, "Missing a team's shot chart"
assert games_collected == 1230, "Missing games in the shot chart"



# Save raw as Parquet (keeps column types, so GAME_ID keeps its leading zeros).
team_log.to_parquet(RAW_DIR / "team_log.parquet")
player_log.to_parquet(RAW_DIR / "player_log.parquet")
shot_chart.to_parquet(RAW_DIR / "shot_chart.parquet")
print("Saved 3 files to", RAW_DIR)