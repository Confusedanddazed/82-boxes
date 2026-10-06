-- views.sql
-- Views that calculate team stats, scores and point differential from the player rows.
-- Nothing here is stored: each view runs its query fresh whenever it is used.

-- 1. Team totals per game: add up every player's stats for each (game, team)
CREATE OR REPLACE VIEW team_game_stats AS
SELECT game_id,
       team_id,
       SUM(pts)  AS pts,
       SUM(fgm)  AS fgm,
       SUM(fga)  AS fga,
       SUM(fg3m) AS fg3m,
       SUM(fg3a) AS fg3a,
       SUM(ftm)  AS ftm,
       SUM(fta)  AS fta,
       SUM(oreb) AS oreb,
       SUM(dreb) AS dreb,
       SUM(ast)  AS ast,
       SUM(stl)  AS stl,
       SUM(blk)  AS blk,
       SUM(tov)  AS tov,
       SUM(pf)   AS pf
FROM player_game_stats
GROUP BY game_id, team_id;

-- 2. One row per game: home and away points, and the point differential.
-- point_diff is home points minus away points, so a positive number means the home team won.
CREATE OR REPLACE VIEW game_scores AS
SELECT g.game_id,
       g.game_date,
       g.home_team_id,
       g.away_team_id,
       g.neutral_site,
       h.pts AS home_pts,
       a.pts AS away_pts,
       h.pts - a.pts AS point_diff
FROM games g
JOIN team_game_stats h ON h.game_id = g.game_id AND h.team_id = g.home_team_id
JOIN team_game_stats a ON a.game_id = g.game_id AND a.team_id = g.away_team_id;

-- 3. One row per team per game, from that team's point of view.
-- The first SELECT is every game from the home team's side, the second is the same
-- games from the away team's side (point differential flipped). UNION ALL stacks them.
CREATE OR REPLACE VIEW team_games AS
SELECT game_id,
       game_date,
       home_team_id AS team_id,
       away_team_id AS opponent_id,
       TRUE         AS is_home,
       neutral_site,
       home_pts     AS pts_for,
       away_pts     AS pts_against,
       point_diff,
       point_diff > 0 AS won
FROM game_scores
UNION ALL
SELECT game_id,
       game_date,
       away_team_id,
       home_team_id,
       FALSE,
       neutral_site,
       away_pts,
       home_pts,
       -point_diff,
       point_diff < 0
FROM game_scores;


-- 4. Game Score for every player-game, plus its percentile.
-- Game Score is calculated here, not stored. The percentile compares a game against
-- every player-game in the season with 5 or more minutes (the "pool").
-- PERCENT_RANK gives 0 to 1: 0.99 means better than 99% of the pool.
-- Games under 5 minutes get no percentile (NULL), so they don't distort the scale.
CREATE OR REPLACE VIEW player_game_scores AS
WITH scored AS (
    SELECT game_id, player_id, team_id, min,
           pts + 0.4 * fgm - 0.7 * fga - 0.4 * (fta - ftm)
               + 0.7 * oreb + 0.3 * dreb + stl + 0.7 * ast + 0.7 * blk
               - 0.4 * pf - tov AS game_score
    FROM player_game_stats
),
pool AS (
    SELECT game_id, player_id,
           PERCENT_RANK() OVER (ORDER BY game_score) AS game_score_pctile
    FROM scored
    WHERE min >= 5
)
SELECT s.game_id, s.player_id, s.team_id, s.min, s.game_score, p.game_score_pctile
FROM scored s
LEFT JOIN pool p ON p.game_id = s.game_id AND p.player_id = s.player_id;

-- 5. Standings: one row per team, ranked against all 30 teams together.
-- Ranked by wins, then total point differential to break ties.
CREATE OR REPLACE VIEW team_standings AS
SELECT t.team_id,
       t.full_name,
       t.abbreviation,
       COUNT(*)                                          AS games,
       SUM(CASE WHEN tg.won THEN 1 ELSE 0 END)           AS wins,
       SUM(CASE WHEN tg.won THEN 0 ELSE 1 END)           AS losses,
       ROUND(AVG(tg.won::int), 3)                        AS win_pct,
       SUM(tg.point_diff)                                AS total_point_diff,
       ROUND(AVG(tg.point_diff), 1)                      AS avg_point_diff,
       RANK() OVER (ORDER BY SUM(CASE WHEN tg.won THEN 1 ELSE 0 END) DESC,
                             SUM(tg.point_diff) DESC)    AS league_rank
FROM teams t
JOIN team_games tg ON tg.team_id = t.team_id
GROUP BY t.team_id, t.full_name, t.abbreviation;

-- 6. Each player's season stats for each team (the team page table).
-- Grouping by team and player means a traded player gets one row for each team,
-- counting only the games he played for that team.
-- Totals are sums of the raw counts; per-game numbers and percentages are calculated here.
CREATE OR REPLACE VIEW team_player_season_stats AS
SELECT pgs.team_id,
       pgs.player_id,
       p.player_name,
       COUNT(*)                                                       AS gp,
       ROUND(AVG(pgs.min), 1)                                         AS mpg,
       SUM(pgs.pts)                                                   AS pts,
       SUM(pgs.oreb + pgs.dreb)                                       AS reb,
       SUM(pgs.ast)                                                   AS ast,
       SUM(pgs.stl)                                                   AS stl,
       SUM(pgs.blk)                                                   AS blk,
       SUM(pgs.tov)                                                   AS tov,
       SUM(pgs.pf)                                                    AS pf,
       SUM(pgs.fgm)                                                   AS fgm,
       SUM(pgs.fga)                                                   AS fga,
       SUM(pgs.fg3m)                                                  AS fg3m,
       SUM(pgs.fg3a)                                                  AS fg3a,
       SUM(pgs.ftm)                                                   AS ftm,
       SUM(pgs.fta)                                                   AS fta,
       ROUND(AVG(pgs.pts), 1)                                         AS ppg,
       ROUND(AVG(pgs.oreb + pgs.dreb), 1)                             AS rpg,
       ROUND(AVG(pgs.ast), 1)                                         AS apg,
       ROUND(100.0 * SUM(pgs.fgm)  / NULLIF(SUM(pgs.fga), 0), 1)      AS fg_pct,
       ROUND(100.0 * SUM(pgs.fg3m) / NULLIF(SUM(pgs.fg3a), 0), 1)     AS fg3_pct,
       ROUND(100.0 * SUM(pgs.ftm)  / NULLIF(SUM(pgs.fta), 0), 1)      AS ft_pct
FROM player_game_stats pgs
JOIN players p ON p.player_id = pgs.player_id
GROUP BY pgs.team_id, pgs.player_id, p.player_name;