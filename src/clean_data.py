"""
clean_data.py
Reads the raw files in data/raw/, builds the five tables, runs 26 checks and saves
the results to data/processed/. If a check fails, the script stops and nothing is saved.
 
Run from the project root (after extract_data.py):  python src/clean_data.py
"""
from datetime import datetime
from pathlib import Path
 
import pandas as pd
from nba_api.stats.static import teams as static_teams

 # Project folders 
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
LOGS = ROOT / "logs"
PROCESSED.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)
 
# Expected numbers for the 2025-26 regular season (from explore.ipynb)
N_GAMES = 1230
N_TEAMS = 30
N_PLAYER_ROWS = 26651
NEUTRAL_GAMES = {"0022500147", "0022500578", "0022500602", "0022501229", "0022501230"}
# Player totals are off by 1 from the team log in these 3 team-games
# Format: (game_id, team_id, stat): player total minus team log
KNOWN_DIFFS = {
    ("0022500243", 1610612755, "DREB"): -1,
    ("0022500792", 1610612745, "FGA"): 1,
    ("0022500792", 1610612766, "BLK"): 1,
}
SUM_COLS = ["PTS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
            "OREB", "DREB", "AST", "STL", "BLK", "TOV", "PF"]
 
results = []
 
 
# Prints PASS or FAIL, adds it to the log, and stops the script on a FAIL
def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    line = f"[{status}] {name}" + (f"  ({detail})" if detail else "")
    print(line)
    results.append(line)
    if not condition:
        (LOGS / "clean_data.log").write_text("\n".join(results), encoding="utf-8")
        raise AssertionError(line)
 
 # Load raw files 
team_log = pd.read_parquet(RAW / "team_log.parquet")
player_log = pd.read_parquet(RAW / "player_log.parquet")
shot_chart = pd.read_parquet(RAW / "shot_chart.parquet")
standings = pd.read_parquet(RAW / "standings.parquet")

 # Checking raw inputs 

 # Columns kept from each file 
team_col = ["SEASON_ID", "TEAM_ID", "TEAM_ABBREVIATION", "GAME_ID", "GAME_DATE", "MATCHUP"] + SUM_COLS
player_col = ["PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "GAME_ID", "MIN", "PLUS_MINUS"] + SUM_COLS
shot_col = ["GAME_ID", "GAME_EVENT_ID", "PLAYER_ID", "TEAM_ID", "PERIOD", "MINUTES_REMAINING",
            "SECONDS_REMAINING", "ACTION_TYPE", "SHOT_TYPE", "SHOT_ZONE_BASIC", "SHOT_ZONE_AREA",
            "SHOT_ZONE_RANGE", "SHOT_DISTANCE", "LOC_X", "LOC_Y", "SHOT_MADE_FLAG", "HTM"]



check("team_log has no missing values", team_log[team_col].isna().sum().sum() == 0)
check("player_log has no missing values", player_log[player_col].isna().sum().sum() == 0)
check("shot_chart has no missing values", shot_chart[shot_col].isna().sum().sum() == 0)
check("every game appears exactly twice", team_log["GAME_ID"].value_counts().eq(2).all())


 # Teams 

 # Names and abbr come from nba_api's built-in team list
teams = (pd.DataFrame(static_teams.get_teams())
         .rename(columns={"id": "team_id"})
         [["team_id", "full_name", "abbreviation", "city", "nickname"]])
check("30 teams", len(teams) == N_TEAMS)

 # Conference comes from standings
conference_of = dict(zip(standings["TeamID"], standings["Conference"]))
teams["conference"] = teams["team_id"].map(conference_of)
check("every team has a conference", teams["conference"].notna().all())
check("15 teams each in the East and West",
      set(teams["conference"]) == {"East", "West"} and teams["conference"].value_counts().eq(15).all())
 
abbr_to_id = dict(zip(teams["abbreviation"], teams["team_id"]))


# Games 

# MATCHUP is "BKN vs. IND" for a home game and "BKN @ TOR" for an away game.
# The 5 neutral-site games have "@" in both rows.
matchup = team_log["MATCHUP"]
first = matchup.str.split(" ").str[0]
last = matchup.str.split(" ").str[-1]
has_at = matchup.str.contains(" @ ", regex=False)
team_log["home_abbr"] = last.where(has_at, first)
team_log["away_abbr"] = first.where(has_at, last)

 # A game is neutral-site if none of its rows say "vs."
team_log["is_home_row"] = matchup.str.contains(" vs. ", regex=False)
neutral_by_game = team_log.groupby("GAME_ID")["is_home_row"].sum().eq(0)

 # One row per game 
games = team_log[["GAME_ID", "GAME_DATE", "SEASON_ID", "home_abbr", "away_abbr"]].drop_duplicates("GAME_ID").copy()
check("1,230 games", len(games) == N_GAMES, f"got {len(games)}")
 
# Double-check the home team against the HTM column in the shot data
htm = shot_chart[["GAME_ID", "HTM"]].drop_duplicates()
check("each game has exactly one HTM in the shot data", htm["GAME_ID"].is_unique)
cross = games.merge(htm, on="GAME_ID")
check("home team matches the shot data HTM in all games", len(cross) == N_GAMES and (cross["home_abbr"] == cross["HTM"]).all())
 
games["neutral_site"] = games["GAME_ID"].map(neutral_by_game)
check("neutral-site games are exactly the 5 known ones", set(games.loc[games["neutral_site"], "GAME_ID"]) == NEUTRAL_GAMES)

# Games table stores team_ids, not abbr
games["home_team_id"] = games["home_abbr"].map(abbr_to_id)
games["away_team_id"] = games["away_abbr"].map(abbr_to_id)
check("every team abbreviation maps to a team id", games[["home_team_id", "away_team_id"]].notna().all().all())

 # Final games table
games = games.rename(columns={"GAME_ID": "game_id"})
games["game_date"] = pd.to_datetime(games["GAME_DATE"]).dt.date
games["season"] = games["SEASON_ID"].str[-4:].astype(int)
games["game_type"] = "Regular Season"
games = games[["game_id", "season", "game_type", "game_date", "home_team_id", "away_team_id", "neutral_site"]]
games[["home_team_id", "away_team_id"]] = games[["home_team_id", "away_team_id"]].astype(int)


 
# Players 

players = player_log[["PLAYER_ID", "PLAYER_NAME"]].drop_duplicates().rename(
    columns={"PLAYER_ID": "player_id", "PLAYER_NAME": "player_name"})
check("each player id has one name", players["player_id"].is_unique)

 #player_game_statss
stat_cols = SUM_COLS + ["PLUS_MINUS"]
pgs = player_log[["GAME_ID", "PLAYER_ID", "TEAM_ID", "MIN"] + stat_cols].copy()
pgs[stat_cols] = pgs[stat_cols].astype("int64")
pgs["MIN"] = pgs["MIN"].round(2)
pgs.columns = [c.lower() for c in pgs.columns]
player_game_stats = pgs
 
check("26,651 player-game rows", len(pgs) == N_PLAYER_ROWS, f"got {len(pgs)}")
check("(game_id, player_id) is unique", not pgs.duplicated(["game_id", "player_id"]).any())
check("player_game_stats: every game_id exists in games", pgs["game_id"].isin(games["game_id"]).all())
check("player_game_stats: every player_id exists in players", pgs["player_id"].isin(players["player_id"]).all())
check("player_game_stats: every team_id exists in teams", pgs["team_id"].isin(teams["team_id"]).all())

 # Each players team has to be one of the two teams in the game
team_games = team_log[["GAME_ID", "TEAM_ID"]].rename(columns=str.lower)
matched = pgs.merge(team_games, on=["game_id", "team_id"])
check("each player's team played in that game", len(matched) == len(pgs))
 
check("points = 2*FGM + 3PM + FTM", (pgs["pts"] == 2 * pgs["fgm"] + pgs["fg3m"] + pgs["ftm"]).all())

# Player totals vs team log 
# Add up the players for each team in each game and compare with the team log
from_players = player_log.groupby(["GAME_ID", "TEAM_ID"])[SUM_COLS].sum()
from_team = team_log.set_index(["GAME_ID", "TEAM_ID"])[SUM_COLS].reindex(from_players.index)
delta = (from_players - from_team).stack()
differences = delta[delta != 0].to_dict()
check("player sums match the team log except the 3 known differences",
      differences == KNOWN_DIFFS, f"found {differences}")


 # Shots 

# Every shot is a field goal attempt, so shots should equal total FGA 
shots = shot_chart[shot_col].drop(columns="HTM").copy()
shots.columns = [c.lower() for c in shots.columns]

check("(game_id, game_event_id) is unique", not shots.duplicated(["game_id", "game_event_id"]).any())
check("shot count equals total FGA in the player log", len(shots) == pgs["fga"].sum(),
      f"{len(shots)} vs {pgs['fga'].sum()}")
check("shots: every game_id exists in games", shots["game_id"].isin(games["game_id"]).all())
check("shots: every player_id exists in players", shots["player_id"].isin(players["player_id"]).all())
check("shots: every team_id exists in teams", shots["team_id"].isin(teams["team_id"]).all())
 
teams.to_parquet(PROCESSED / "teams.parquet", index=False)
games.to_parquet(PROCESSED / "games.parquet", index=False)
players.to_parquet(PROCESSED / "players.parquet", index=False)
player_game_stats.to_parquet(PROCESSED / "player_game_stats.parquet", index=False)
shots.to_parquet(PROCESSED / "shots.parquet", index=False)
 
summary = (f"\nAll {len(results)} checks passed at {datetime.now():%Y-%m-%d %H:%M}. "
           f"teams={len(teams)}, games={len(games)}, players={len(players)}, "
           f"player_game_stats={len(player_game_stats)}, shots={len(shots)}")
print(summary)
(LOGS / "clean_data.log").write_text("\n".join(results) + "\n" + summary, encoding="utf-8")