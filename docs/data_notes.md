# Data Notes

Season: 2025-26 regular season. Source: `nba_api`.

## Early checks

`test_nba_api.py` confirmed that the API is reachable and returns the expected data: 30 teams and all 82 Lakers games, five of which were checked against ESPN.

`explore_columns.py` reviewed the columns in the team and player game logs. The team log has 28 columns. The player log has 26,651 rows and 72 columns, about half of which are not needed. `GAME_ID` has leading zeros, so it is stored as text. `MIN` is a decimal and is stored as `NUMERIC(6,2)`. `MIN_SEC` contains a rounding error (`31:60`) and is not used. No missing values were found in the columns checked.

## Home, away and neutral-site games

Home and away are parsed from `MATCHUP` (`BKN vs. NYK` is a home game, `BKN @ LAL` is an away game). The parsed home team matches the `HTM` column in the shot data for all 1,230 games.

Five games were played at neutral sites, so both team rows contain `@`. These games are flagged with `neutral_site`.

```
GAME_ID     GAME_DATE   TEAM_ABBREVIATION  MATCHUP    home_team  away_team
0022500602  2026-01-18  MEM                ORL @ MEM  MEM        ORL
0022500602  2026-01-18  ORL                ORL @ MEM  MEM        ORL
0022500578  2026-01-15  MEM                MEM @ ORL  ORL        MEM
0022500578  2026-01-15  ORL                MEM @ ORL  ORL        MEM
0022501230  2025-12-13  SAS                SAS @ OKC  OKC        SAS
0022501230  2025-12-13  OKC                SAS @ OKC  OKC        SAS
0022501229  2025-12-13  ORL                NYK @ ORL  ORL        NYK
0022501229  2025-12-13  NYK                NYK @ ORL  ORL        NYK
0022500147  2025-11-01  DET                DAL @ DET  DET        DAL
0022500147  2025-11-01  DAL                DAL @ DET  DET        DAL
```

## Team stats derived from player rows

Team totals will be summed from player rows in SQL. To confirm this approach works, the player sums were calculated in Python and compared to the team log for every team-game.

```
Team-games compared: 2460
Team-games that differ: 3
                       PTS  FGM  FGA  FG3M  FG3A  FTM  FTA  OREB  DREB  AST  STL  BLK  TOV  PF
GAME_ID     TEAM_ID
0022500243  1610612755   0    0    0    0     0     0    0    0     -1    0    0    0    0    0
0022500792  1610612745   0    0    1    0     0     0    0    0     0     0    0    0    0    0
            1610612766   0    0    0    0     0     0    0    0     0     0    0    1    0    0
```

Three team-games differ by one stat each. Points match in all 2,460 team-games, so scores and point differentials are not affected. The cause is unknown. These differences are documented rather than corrected, and `clean_data.py` expects exactly these three.

## Shot chart

A league-wide `ShotChartDetail` request is capped at 102,400 rows, so `extract_data.py` requests one team at a time. The 30 requests total 219,160 shots, which equals total field goal attempts in the player log. Sixteen of the 24 columns are kept. `EVENT_TYPE` is dropped because it duplicates `SHOT_MADE_FLAG`.

## Pipeline

`extract_data.py` calls the API and saves the raw data as Parquet. `explore.ipynb` documents the exploration. `clean_data.py` builds the five final tables and runs the checks. `validate_processed.ipynb` reviews the final tables and compares them to ESPN. Raw files are never edited, and the final tables are produced only by `clean_data.py`. Parquet is used because it preserves `GAME_ID` as text.

## Cleaning results

```
[PASS] team_log has no missing values
[PASS] player_log has no missing values
[PASS] shot_chart has no missing values
[PASS] every game appears exactly twice
[PASS] 30 teams
[PASS] 1,230 games  (got 1230)
[PASS] each game has exactly one HTM in the shot data
[PASS] home team matches the shot data HTM in all games
[PASS] neutral-site games are exactly the 5 known ones
[PASS] every team abbreviation maps to a team id
[PASS] each player id has one name
[PASS] 26,651 player-game rows  (got 26651)
[PASS] (game_id, player_id) is unique
[PASS] every game_id exists in games
[PASS] every player_id exists in players
[PASS] every team_id exists in teams
[PASS] each player's team played in that game
[PASS] points = 2*FGM + 3PM + FTM
[PASS] player sums match the team log except the 3 known differences  (found {('0022500243', 1610612755, 'DREB'): -1, ('0022500792', 1610612745, 'FGA'): 1, ('0022500792', 1610612766, 'BLK'): 1})
[PASS] (game_id, game_event_id) is unique
[PASS] shot count equals total FGA in the player log  (219160 vs 219160)
[PASS] every game_id exists in games
[PASS] every player_id exists in players
[PASS] every team_id exists in teams

All 24 checks passed at 2026-10-05 21:12. teams=30, games=1230, players=582, player_game_stats=26651, shots=219160
```

## ESPN verification

Two checks were made against ESPN: Egor Dëmin's season totals and one full game, Toronto at Brooklyn on 2026-04-12 (`0022501192`).

Dëmin's totals match ESPN exactly.

```
GP : 52
FG : 179 - 449
3P : 124 - 322
PTS: 536
```

Player lines for the game:

```
abbreviation  player_name            min    pts  fgm  fga  fg3m  fg3a  ftm  fta  oreb  dreb  ast  stl  blk  tov  pf
BKN           Tyson Etienne          36.75  20   6    16   2     10    6    8    0     1     4    2    0    1    2
BKN           Chaney Johnson         36.33  16   6    14   0     3     4    5    5     8     2    1    0    1    3
BKN           Malachi Smith          35.52  8    3    9    2     6     0    0    1     4     6    0    0    2    3
BKN           E.J. Liddell           27.38  17   5    10   3     5     4    4    1     3     1    1    0    1    6
BKN           Ben Saraf              26.37  15   6    10   0     1     3    4    2     1     4    2    0    4    6
BKN           Jalen Wilson           26.35  9    3    9    0     0     3    6    3     5     3    1    0    2    5
BKN           Trevon Scott           26.05  8    3    8    2     5     0    0    1     2     1    1    0    2    2
BKN           Drake Powell           25.25  8    3    10   0     4     2    2    0     1     0    1    0    2    0
TOR           Brandon Ingram         32.00  25   7    10   3     5     8    8    1     8     2    0    1    1    1
TOR           Scottie Barnes         31.99  18   8    11   0     0     2    2    0     12    12   1    3    1    0
TOR           RJ Barrett             28.62  26   9    15   2     5     6    9    1     2     2    0    0    1    5
TOR           Ja'Kobe Walter         24.12  11   3    5    3     5     2    2    0     0     1    1    1    1    2
TOR           Jamal Shead            20.18  6    3    6    0     2     0    0    0     1     4    1    1    2    2
TOR           Jakob Poeltl           19.25  11   5    5    0     0     1    5    0     5     2    2    1    3    2
TOR           Sandro Mamukelashvili  17.63  9    4    5    1     2     0    0    0     3     3    0    0    0    1
TOR           Immanuel Quickley      16.65  4    2    6    0     2     0    0    0     2     5    2    0    1    0
TOR           Collin Murray-Boyles   13.41  2    0    0    0     0     2    2    0     2     2    0    0    0    5
TOR           A.J. Lawson            10.63  10   4    6    2     4     0    0    0     0     0    0    0    0    1
TOR           Trayce Jackson-Davis   5.30   4    2    3    0     0     0    0    1     3     0    0    1    0    1
TOR           Jonathan Mogbo         5.30   2    1    1    0     0     0    0    0     1     2    1    0    0    0
TOR           Gradey Dick            5.30   3    1    4    0     0     1    1    0     0     0    0    0    0    0
TOR           Jamison Battle         5.30   2    1    2    0     1     0    0    0     0     0    0    0    0    0
TOR           Garrett Temple         4.32   3    1    1    1     1     0    0    0     1     1    1    0    0    0
```

Team totals summed from those player rows:

```
              pts  fgm  fga  fg3m  fg3a  ftm  fta  oreb  dreb  ast  stl  blk  tov  pf
abbreviation
BKN           101   35   86     9    34   22   29    13    25   21    9    0   15  27
TOR           136   51   80    12    27   22   29     3    40   36    9    8   10  20
```

All 23 player lines and both team total rows match the [ESPN box score](https://www.espn.com/nba/boxscore/_/gameId/401811047), apart from minutes, which ESPN rounds to whole numbers. The final score of Toronto 136, Brooklyn 101 matches, and each team's minutes total 240.

Four Brooklyn players are listed on ESPN as did not play (Claxton, Sharpe, Agbaji and Traore). They have no rows in the player log, so they are shown as "not listed in box score" in the heatmaps.

## Next step

Set up PostgreSQL, create the tables from the ER diagram, and load the five processed tables.