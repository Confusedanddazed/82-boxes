"""
clean_data.py
Reads the raw files in data/raw/, builds the five tables from the ERD, runs checks on
everything, and saves the results to data/processed/. If a check fails the script
stops and nothing gets saved.

Run from the project root (after extract_data.py):  python src/clean_data.py
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
from nba_api.stats.static import teams as static_teams

# Paths to the project folders (ROOT = the 82-boxes folder)
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
LOGS = ROOT / "logs"
PROCESSED.mkdir(parents=True, exist_ok=True)  # makes the folder if it isn't there yet
LOGS.mkdir(parents=True, exist_ok=True)

# Numbers I found in explore.ipynb for the 2025-26 regular season, used in the checks below
N_GAMES = 1230
N_TEAMS = 30
N_PLAYER_ROWS = 26651
NEUTRAL_GAMES = {"0022500147", "0022500578", "0022500602", "0022501229", "0022501230"}  # the 5 games with no home team
# The 3 team-games where the player sums are off by 1 from the team log (Section 4 of explore.ipynb)
# Format: (game_id, team_id, stat): player sum minus team log
KNOWN_DIFFS = {
    ("0022500243", 1610612755, "DREB"): -1,
    ("0022500792", 1610612745, "FGA"): 1,
    ("0022500792", 1610612766, "BLK"): 1,
}
# The 14 counting stats I add up from players to get team stats
SUM_COLS = ["PTS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
            "OREB", "DREB", "AST", "STL", "BLK", "TOV", "PF"]

# Helper that runs a check: prints PASS or FAIL, saves it to a list for the log file,
# and stops the whole script if the check fails
results = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"  # condition is True or False
    line = f"[{status}] {name}" + (f"  ({detail})" if detail else "")  # detail is optional extra info
    print(line)
    results.append(line)
    if not condition:
        # save everything that ran so far to the log, then stop with an error
        (LOGS / "clean_data.log").write_text("\n".join(results), encoding="utf-8")
        raise AssertionError(line)


# Load the raw files that extract_data.py saved
team_log = pd.read_parquet(RAW / "team_log.parquet")
player_log = pd.read_parquet(RAW / "player_log.parquet")
shot_chart = pd.read_parquet(RAW / "shot_chart.parquet")

# ---------- Raw input checks ----------
# The columns I'm keeping from each file. Picking a column that doesn't exist gives an error on its own.
team_col = ["SEASON_ID", "TEAM_ID", "TEAM_ABBREVIATION", "GAME_ID", "GAME_DATE", "MATCHUP"] + SUM_COLS
player_col = ["PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "GAME_ID", "MIN", "PLUS_MINUS"] + SUM_COLS
shot_col = ["GAME_ID", "GAME_EVENT_ID", "PLAYER_ID", "TEAM_ID", "PERIOD", "MINUTES_REMAINING",
            "SECONDS_REMAINING", "ACTION_TYPE", "SHOT_TYPE", "SHOT_ZONE_BASIC", "SHOT_ZONE_AREA",
            "SHOT_ZONE_RANGE", "SHOT_DISTANCE", "LOC_X", "LOC_Y", "SHOT_MADE_FLAG", "HTM"]

# isna() marks missing values as True, first sum() counts them per column, second sum() adds them up. 0 = none missing
check("team_log has no missing values", team_log[team_col].isna().sum().sum() == 0)
check("player_log has no missing values", player_log[player_col].isna().sum().sum() == 0)
check("shot_chart has no missing values", shot_chart[shot_col].isna().sum().sum() == 0)

# Each game is in the team log twice, once for each team. value_counts() = how many times each GAME_ID shows up
check("every game appears exactly twice", team_log["GAME_ID"].value_counts().eq(2).all())

# ---------- TEAMS ----------
# Team info (name, abbreviation, city) comes from nba_api's built-in list of teams
teams = (pd.DataFrame(static_teams.get_teams())
         .rename(columns={"id": "team_id"})
         [["team_id", "full_name", "abbreviation", "city", "nickname"]])
check("30 teams", len(teams) == N_TEAMS)
# dictionary to look up a team id from its abbreviation, like {"BKN": 1610612751, ...}
abbr_to_id = dict(zip(teams["abbreviation"], teams["team_id"]))

# ---------- GAMES ----------
# MATCHUP is "BKN vs. IND" for a home game or "BKN @ TOR" for an away game.
# The 5 neutral-site games have "@" in both rows, with the away team listed first.
matchup = team_log["MATCHUP"]
first = matchup.str.split(" ").str[0]   # splits the text at the spaces, [0] = first word (the team in this row)
last = matchup.str.split(" ").str[-1]   # [-1] = last word (the opponent)
has_at = matchup.str.contains(" @ ", regex=False)  # True if the row is an away game
# .where(has_at, first) = use "last" where it's True, otherwise use "first"
team_log["home_abbr"] = last.where(has_at, first)
team_log["away_abbr"] = first.where(has_at, last)

# A game is neutral-site if none of its rows say "vs."
team_log["is_home_row"] = matchup.str.contains(" vs. ", regex=False)
# groupby GAME_ID then sum the True values. 0 means no home row for that game
neutral_by_game = team_log.groupby("GAME_ID")["is_home_row"].sum().eq(0)

# One row per game: both teams' rows give the same info, so drop_duplicates keeps just one of each GAME_ID
games = team_log[["GAME_ID", "GAME_DATE", "SEASON_ID", "home_abbr", "away_abbr"]].drop_duplicates("GAME_ID").copy()
check("1,230 games", len(games) == N_GAMES, f"got {len(games)}")

# Second source to double check my home team: the shot data has a HTM (home team) column
htm = shot_chart[["GAME_ID", "HTM"]].drop_duplicates()
check("each game has exactly one HTM in the shot data", htm["GAME_ID"].is_unique)
cross = games.merge(htm, on="GAME_ID")  # joins the two tables on GAME_ID
check("home team matches the shot data HTM in all games", len(cross) == N_GAMES and (cross["home_abbr"] == cross["HTM"]).all())

# .map(neutral_by_game) looks up each GAME_ID in that True/False table
games["neutral_site"] = games["GAME_ID"].map(neutral_by_game)
check("neutral-site games are exactly the 5 known ones", set(games.loc[games["neutral_site"], "GAME_ID"]) == NEUTRAL_GAMES)

# swap abbreviations for team ids (the games table stores ids, not abbreviations)
games["home_team_id"] = games["home_abbr"].map(abbr_to_id)
games["away_team_id"] = games["away_abbr"].map(abbr_to_id)
check("every team abbreviation maps to a team id", games[["home_team_id", "away_team_id"]].notna().all().all())

# Final games table: lowercase names, a real date, the season as a number (SEASON_ID "22025" -> last 4 characters -> 2025)
games = games.rename(columns={"GAME_ID": "game_id"})
games["game_date"] = pd.to_datetime(games["GAME_DATE"]).dt.date
games["season"] = games["SEASON_ID"].str[-4:].astype(int)
games["game_type"] = "Regular Season"
games = games[["game_id", "season", "game_type", "game_date", "home_team_id", "away_team_id", "neutral_site"]]
games[["home_team_id", "away_team_id"]] = games[["home_team_id", "away_team_id"]].astype(int)

# ---------- PLAYERS ----------
# One row per player: take id and name from the player log, remove repeats
players = player_log[["PLAYER_ID", "PLAYER_NAME"]].drop_duplicates().rename(
    columns={"PLAYER_ID": "player_id", "PLAYER_NAME": "player_name"})
check("each player id has one name", players["player_id"].is_unique)

# ---------- PLAYER_GAME_STATS ----------
stat_cols = SUM_COLS + ["PLUS_MINUS"]
pgs = player_log[["GAME_ID", "PLAYER_ID", "TEAM_ID", "MIN"] + stat_cols].copy()  # .copy() so changes don't touch player_log
pgs[stat_cols] = pgs[stat_cols].astype("int64")  # make sure the stats are whole numbers
pgs["MIN"] = pgs["MIN"].round(2)                 # 38.283333 -> 38.28
# c is each column name as it loops through them, c.lower() makes it lowercase (GAME_ID -> game_id)
pgs.columns = [c.lower() for c in pgs.columns]
player_game_stats = pgs

check("26,651 player-game rows", len(pgs) == N_PLAYER_ROWS, f"got {len(pgs)}")
check("(game_id, player_id) is unique", not pgs.duplicated(["game_id", "player_id"]).any())
# .isin() = is each value found in the other table's column
check("player_game_stats: every game_id exists in games", pgs["game_id"].isin(games["game_id"]).all())
check("player_game_stats: every player_id exists in players", pgs["player_id"].isin(players["player_id"]).all())
check("player_game_stats: every team_id exists in teams", pgs["team_id"].isin(teams["team_id"]).all())

# Each player's team must be one of the teams that played that game.
# str.lower on the column names turns GAME_ID, TEAM_ID into game_id, team_id so the two tables can join.
# If every row finds a match in the merge, the row count stays the same.
team_games = team_log[["GAME_ID", "TEAM_ID"]].rename(columns=str.lower)
matched = pgs.merge(team_games, on=["game_id", "team_id"])
check("each player's team played in that game", len(matched) == len(pgs))

# points should equal 2 for every made shot + 1 extra for every three + free throws
check("points = 2*FGM + 3PM + FTM", (pgs["pts"] == 2 * pgs["fgm"] + pgs["fg3m"] + pgs["ftm"]).all())

# ---------- Team stats from player rows vs the team log ----------
# add up the players for each (game, team), then compare with what the team log says
from_players = player_log.groupby(["GAME_ID", "TEAM_ID"])[SUM_COLS].sum()
from_team = team_log.set_index(["GAME_ID", "TEAM_ID"])[SUM_COLS].reindex(from_players.index)  # reindex = same row order as above
# subtract the two tables. stack() turns the columns into rows so each stat gets its own row
delta = (from_players - from_team).stack()
# keep only the nonzero differences, and turn them into a dictionary like KNOWN_DIFFS
differences = delta[delta != 0].to_dict()
check("player sums match the team log except the 3 known differences",
      differences == KNOWN_DIFFS, f"found {differences}")

# ---------- SHOTS ----------
shots = shot_chart[shot_col].drop(columns="HTM").copy()  # HTM was only needed for the home team check
shots.columns = [c.lower() for c in shots.columns]
check("(game_id, game_event_id) is unique", not shots.duplicated(["game_id", "game_event_id"]).any())
# every shot is a field goal attempt, so shots should equal the total FGA from the players
check("shot count equals total FGA in the player log", len(shots) == pgs["fga"].sum(),
      f"{len(shots)} vs {pgs['fga'].sum()}")
check("shots: every game_id exists in games", shots["game_id"].isin(games["game_id"]).all())
check("shots: every player_id exists in players", shots["player_id"].isin(players["player_id"]).all())
check("shots: every team_id exists in teams", shots["team_id"].isin(teams["team_id"]).all())

# ---------- Save ----------
teams.to_parquet(PROCESSED / "teams.parquet", index=False)
games.to_parquet(PROCESSED / "games.parquet", index=False)
players.to_parquet(PROCESSED / "players.parquet", index=False)
player_game_stats.to_parquet(PROCESSED / "player_game_stats.parquet", index=False)
shots.to_parquet(PROCESSED / "shots.parquet", index=False)

# Final message and the log file with every check that passed
summary = (f"\nAll {len(results)} checks passed at {datetime.now():%Y-%m-%d %H:%M}. "
           f"teams={len(teams)}, games={len(games)}, players={len(players)}, "
           f"player_game_stats={len(player_game_stats)}, shots={len(shots)}")
print(summary)
(LOGS / "clean_data.log").write_text("\n".join(results) + "\n" + summary, encoding="utf-8")