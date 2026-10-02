from nba_api.stats.endpoints import leaguegamefinder, playergamelogs
#
games= leaguegamefinder.LeagueGameFinder(
    season_nullable="2025-26",
    season_type_nullable="Regular Season",
    timeout=30,
).get_data_frames()[0]

print("Team Game Columns:")
print(list(games.columns))
# Contains plus_minus stat needed for team boxes.

players = playergamelogs.PlayerGameLogs(
    season_nullable="2025-26",
    season_type_nullable="Regular Season",
    timeout=60,
).get_data_frames()[0]

print(f"\nPlayer Game Rows (whole league): {len(players)}")
print("Player Game Columns:")
print(list(players.columns))
# Contains basic player data for each game, we can use these stats to calculate and 
# populate players boxes with their respective Game Score. 

# Gives us the correct data type for each column in games and players. 
print(games.dtypes)
print(players.dtypes)
# Selecting necessary columns and noting their data types.
# INTEGER: team_id, player_id, season, home_score, away_score, plus_minus, all stats relating to box score
# DATE: game_date
# VARCHAR(20): game_type
# VARCHAR(10): game_id
# NUMERIC(6,2): min

cols = ["PLAYER_ID", "TEAM_ID", "MIN", "PTS", "FGM", "FGA", "FG3M", "FG3A",
        "FTM", "FTA", "OREB", "DREB", "AST", "STL", "BLK", "TOV", "PF", "PLUS_MINUS"]

team_cols = ["SEASON_ID", "TEAM_ID", "GAME_ID", "GAME_DATE", "MATCHUP", "PTS", "PLUS_MINUS"]

# Checking for missing values.
print(players[cols].isna().sum()) # 0 missing values 
print(games[team_cols].isna().sum()) # 0 missing values 
print("League-wide team rows:", len(games)) # 2460 rows (30 teams x 82 games)
print("League-wide player rows:", len(players)) #26,651 rows ()
assert len(games) > 0, "No team rows returned, check the API call"
assert len(players) > 0, "No player rows returned, check the API call"