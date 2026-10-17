# head 2 head: Power BI Measures

Player 1 measures use `players`. Player 2 measures use `player_b`, a copy of `players` with no relationships, and apply the selection with `TREATAS`.

## Averages
Season averages and shooting percentages.

```
GP             = CALCULATE ( COUNTROWS ( player_games ), player_games[played] = TRUE () )
MPG            = AVERAGE ( player_games[min] )
PPG            = AVERAGE ( player_games[pts] )
RPG            = AVERAGE ( player_games[reb] )
APG            = AVERAGE ( player_games[ast] )
Avg Game Score = AVERAGE ( player_games[game_score] )
FG%            = DIVIDE ( SUM ( player_games[fgm] ),  SUM ( player_games[fga] ) )
3P%            = DIVIDE ( SUM ( player_games[fg3m] ), SUM ( player_games[fg3a] ) )
FT%            = DIVIDE ( SUM ( player_games[ftm] ),  SUM ( player_games[fta] ) )
```

```
STL     = AVERAGE ( player_games[stl] )
BLK     = AVERAGE ( player_games[blk] )
TOV     = AVERAGE ( player_games[tov] )
FGM     = AVERAGE ( player_games[fgm] )
FGA     = AVERAGE ( player_games[fga] )
3PM     = AVERAGE ( player_games[fg3m] )
3PA     = AVERAGE ( player_games[fg3a] )
FTM     = AVERAGE ( player_games[ftm] )
FTA     = AVERAGE ( player_games[fta] )
+/-     = AVERAGE ( player_games[plus_minus] )
High PTS = MAX ( player_games[pts] )
AST/TO  = DIVIDE ( SUM ( player_games[ast] ), SUM ( player_games[tov] ) )
eFG%    = DIVIDE ( SUM ( player_games[fgm] ) + 0.5 * SUM ( player_games[fg3m] ), SUM ( player_games[fga] ) )
TS%     = DIVIDE ( SUM ( player_games[pts] ), 2 * ( SUM ( player_games[fga] ) + 0.44 * SUM ( player_games[fta] ) ) )
```

## Games and form
Games played, double-doubles, triple-doubles, and the last 5 games compared with the season average.

```
Games Played = CALCULATE ( COUNTROWS ( player_games ), player_games[min] > 0 )
```

```
Double Doubles =
SUMX (
    player_games,
    IF (
        ( player_games[pts] >= 10 ) + ( player_games[reb] >= 10 ) + ( player_games[ast] >= 10 )
            + ( player_games[stl] >= 10 ) + ( player_games[blk] >= 10 ) >= 2,
        1, 0
    )
)

Triple Doubles =
SUMX (
    player_games,
    IF (
        ( player_games[pts] >= 10 ) + ( player_games[reb] >= 10 ) + ( player_games[ast] >= 10 )
            + ( player_games[stl] >= 10 ) + ( player_games[blk] >= 10 ) >= 3,
        1, 0
    )
)
```

```
Last 5 PPG =
VAR played = FILTER ( player_games, player_games[min] > 0 )
VAR last5  = TOPN ( 5, played, RELATED ( team_games[game_date] ), DESC )
RETURN
    AVERAGEX ( last5, player_games[pts] )

Form Delta = [Last 5 PPG] - [PPG]
```

## Team lookups
The team from the player's most recent game, and its details from `team_standings`.

```
Current Team ID =
VAR lastKey =
    MAXX (
        TOPN ( 1, ADDCOLUMNS ( player_games, "d", RELATED ( team_games[game_date] ) ), [d], DESC ),
        player_games[team_game_key]
    )
RETURN
    LOOKUPVALUE ( team_games[team_id], team_games[team_game_key], lastKey )
```

```
Team Name = LOOKUPVALUE ( team_standings[full_name],       team_standings[team_id], [Current Team ID] )
Team Logo = LOOKUPVALUE ( team_standings[logo_url],        team_standings[team_id], [Current Team ID] )
Team Conf = LOOKUPVALUE ( team_standings[conference],      team_standings[team_id], [Current Team ID] )
Team Seed = LOOKUPVALUE ( team_standings[conference_rank], team_standings[team_id], [Current Team ID] )
```

```
Team Season Record =
VAR w = LOOKUPVALUE ( team_standings[wins],   team_standings[team_id], [Current Team ID] )
VAR l = LOOKUPVALUE ( team_standings[losses], team_standings[team_id], [Current Team ID] )
RETURN
    w & "–" & l

Team Record =
VAR played = FILTER ( player_games, player_games[min] > 0 )
VAR wins   = SUMX ( played, IF ( RELATED ( team_games[won] ), 1, 0 ) )
RETURN
    wins & "–" & ( COUNTROWS ( played ) - wins )
```

## Card strings
One text value per card with the stats separated by `|`, which the Deneb card splits apart.

```
Stats Core =
IF (
    HASONEVALUE ( player_games[player_name] ),
    [Team Name] & "|" & [Team Logo] & "|" & FORMAT ( [Games Played], "0" ) & "|" & [Games Played] & " of 82" & "|" & [Team Record] & "|"
        & FORMAT ( [Last 5 PPG], "0.0000" ) & "|" & FORMAT ( [Form Delta], "0.0000" ) & "|"
        & FORMAT ( [PPG], "0.0000" ) & "|" & FORMAT ( [RPG], "0.0000" ) & "|" & FORMAT ( [APG], "0.0000" ) & "|"
        & FORMAT ( [Avg Game Score], "0.0000" ) & "|" & FORMAT ( [STL], "0.0000" ) & "|" & FORMAT ( [BLK], "0.0000" ) & "|"
        & FORMAT ( [TOV], "0.0000" ) & "|" & FORMAT ( [AST/TO], "0.0000" ) & "|" & FORMAT ( [MPG], "0.0000" ) & "|"
        & FORMAT ( [FGM], "0.0000" ) & "|" & FORMAT ( [FGA], "0.0000" ) & "|"
        & FORMAT ( [3PM], "0.0000" ) & "|" & FORMAT ( [3PA], "0.0000" ) & "|"
        & FORMAT ( [FTM], "0.0000" ) & "|" & FORMAT ( [FTA], "0.0000" ) & "|"
        & FORMAT ( [FG%], "0.0000" ) & "|" & FORMAT ( [3P%], "0.0000" ) & "|" & FORMAT ( [FT%], "0.0000" ) & "|"
        & FORMAT ( [eFG%], "0.0000" ) & "|" & FORMAT ( [TS%], "0.0000" ) & "|"
        & FORMAT ( [High PTS], "0" ) & "|" & FORMAT ( [Double Doubles], "0" ) & "|" & FORMAT ( [Triple Doubles], "0" ) & "|"
        & FORMAT ( [+/-], "0.0000" )
)
```

```
Stats A =
IF (
    HASONEVALUE ( players[player_name] ),
    [Stats Core]
        & "|" & MAX ( players[PPG Rank] )
        & "|" & MAX ( players[RPG Rank] )
        & "|" & MAX ( players[APG Rank] )
        & "|" & [Team Conf]
        & "|" & [Team Seed]
        & "|" & [Team Season Record]
)
```

```
Stats B =
VAR who = VALUES ( player_b[player_name] )
RETURN
    IF (
        HASONEVALUE ( player_b[player_name] ),
        CALCULATE ( [Stats Core], REMOVEFILTERS ( players ), TREATAS ( who, player_games[player_name] ) )
            & "|" & CALCULATE ( MAX ( players[PPG Rank] ), REMOVEFILTERS ( players ), TREATAS ( who, players[player_name] ) )
            & "|" & CALCULATE ( MAX ( players[RPG Rank] ), REMOVEFILTERS ( players ), TREATAS ( who, players[player_name] ) )
            & "|" & CALCULATE ( MAX ( players[APG Rank] ), REMOVEFILTERS ( players ), TREATAS ( who, players[player_name] ) )
            & "|" & CALCULATE ( [Team Conf], REMOVEFILTERS ( players ), TREATAS ( who, player_games[player_name] ) )
            & "|" & CALCULATE ( [Team Seed], REMOVEFILTERS ( players ), TREATAS ( who, player_games[player_name] ) )
            & "|" & CALCULATE ( [Team Season Record], REMOVEFILTERS ( players ), TREATAS ( who, player_games[player_name] ) )
    )
```

## Who is picked
Blanks the visuals when no player is selected.

```
Name A = SELECTEDVALUE ( players[player_name] )
Name B = SELECTEDVALUE ( player_b[player_name] )

P1 Picked =
IF ( CALCULATE ( DISTINCTCOUNT ( players[player_name] ), ALLSELECTED ( players ) ) = 1, 1 )

P2 Picked =
IF ( CALCULATE ( DISTINCTCOUNT ( player_b[player_name] ), ALLSELECTED ( player_b ) ) = 1, 1 )

Shot In P1 = IF ( MAX ( shot_events[player_id] ) IN VALUES ( players[player_id] ), 1, 0 )
Shot In P2 = IF ( MAX ( shot_events[player_id] ) IN VALUES ( player_b[player_id] ), 1, 0 )
```

## Heatmaps
Game Score percentile for Player 2's heatmap.

```
Player Played =
IF ( ISFILTERED ( player_games[player_name] ), COUNTROWS ( player_games ), 1 )

Player Played B =
IF (
    HASONEVALUE ( player_b[player_name] ),
    VAR n =
        CALCULATE (
            COUNTROWS ( player_games ),
            REMOVEFILTERS ( players ),
            TREATAS ( VALUES ( player_b[player_name] ), player_games[player_name] ),
            NOT ISBLANK ( player_games[game_score_pct] )
        )
    RETURN
        IF ( n > 0, n )
)

GS Pctl B =
VAR who = VALUES ( player_b[player_name] )
RETURN
    IF (
        HASONEVALUE ( player_b[player_name] ),
        CALCULATE (
            MAX ( player_games[game_score_pct] ),
            REMOVEFILTERS ( players ),
            TREATAS ( who, player_games[player_name] )
        )
    )
```

## Rolling trend chart
The stat picker chooses the stat. Player 2 versions are at the bottom.

```
Stat Label = SELECTEDVALUE ( 'Stat Picker'[Stat], "PTS" )

Stat Value =
VAR s = SELECTEDVALUE ( 'Stat Picker'[Stat], "PTS" )
VAR v =
    SWITCH (
        s,
        "PTS", SUM ( player_games[pts] ),
        "REB", SUM ( player_games[reb] ),
        "AST", SUM ( player_games[ast] ),
        "STL", SUM ( player_games[stl] ),
        "BLK", SUM ( player_games[blk] ),
        "TOV", SUM ( player_games[tov] ),
        "3PM", SUM ( player_games[fg3m] ),
        "GmSc", SUM ( player_games[game_score] )
    )
RETURN
    IF ( SUM ( player_games[min] ) > 0, v )

Stat Season Avg =
VAR s = SELECTEDVALUE ( 'Stat Picker'[Stat], "PTS" )
VAR g =
    FILTER (
        CALCULATETABLE ( player_games, ALLEXCEPT ( player_games, player_games[player_name] ) ),
        player_games[min] > 0
    )
RETURN
    SWITCH (
        s,
        "PTS", AVERAGEX ( g, player_games[pts] ),
        "REB", AVERAGEX ( g, player_games[reb] ),
        "AST", AVERAGEX ( g, player_games[ast] ),
        "STL", AVERAGEX ( g, player_games[stl] ),
        "BLK", AVERAGEX ( g, player_games[blk] ),
        "TOV", AVERAGEX ( g, player_games[tov] ),
        "3PM", AVERAGEX ( g, player_games[fg3m] ),
        "GmSc", AVERAGEX ( g, player_games[game_score] )
    )
```

```
Stat Value B =
VAR who = VALUES ( player_b[player_name] )
RETURN
    IF (
        HASONEVALUE ( player_b[player_name] ),
        CALCULATE ( [Stat Value], REMOVEFILTERS ( players ), TREATAS ( who, player_games[player_name] ) )
    )

Stat Season Avg B =
VAR who = VALUES ( player_b[player_name] )
RETURN
    IF (
        HASONEVALUE ( player_b[player_name] ),
        CALCULATE ( [Stat Season Avg], REMOVEFILTERS ( players ), TREATAS ( who, player_games[player_name] ) )
    )

Stat Either = IF ( NOT ISBLANK ( [Stat Value] ) || NOT ISBLANK ( [Stat Value B] ), 1 )
```

## Calculated columns and tables

```
PPG Rank =
VAR v = CALCULATE ( [PPG] )
RETURN
    IF ( NOT ISBLANK ( v ), COUNTROWS ( FILTER ( ALL ( players ), CALCULATE ( [PPG] ) > v ) ) + 1 )
```

```
opponent_logo = LOOKUPVALUE ( team_standings[logo_url],     team_standings[team_id], team_games[opponent_id] )
opponent      = LOOKUPVALUE ( team_standings[abbreviation], team_standings[team_id], team_games[opponent_id] )
```

```
player_b = players
```

`Stat Picker` is an entered table with one column, `Stat`: PTS, REB, AST, STL, BLK, TOV, 3PM, GmSc.
