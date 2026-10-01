from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder

# 
nba_teams = teams.get_teams()
print(f"Teams found: {len(nba_teams)}")
print(nba_teams[0])

# Part 2: live API call (checks we can actually reach the NBA)
lakers_id = 1610612747
finder = leaguegamefinder.LeagueGameFinder(
    team_id_nullable=lakers_id,
    season_nullable="2025-26",
    season_type_nullable="Regular Season",
    timeout=30,
)
games = finder.get_data_frames()[0]

print(f"\nGames returned: {len(games)}")
print(games[["GAME_DATE", "MATCHUP", "WL", "PTS"]].head())