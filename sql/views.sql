-- views.sql
-- Views that calculate team stats, scores and point differential from the player rows.
-- Nothing here is stored: each view runs its query fresh whenever it is used.

-- Drop first so the views can be rebuilt even when columns change.
-- Every view that depends on another is listed in the same statement, so the order is safe.
DROP VIEW IF EXISTS shot_events, player_games, team_player_season_stats, team_standings,
                    player_game_scores, team_games, game_scores, team_game_stats;

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
-- game_number counts each team's games in date order (1 to 82). grid_row and grid_col
-- place each game in a grid with 10 boxes per row, for the heatmap.
CREATE OR REPLACE VIEW team_games AS
WITH both_sides AS (
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
    FROM game_scores
),
numbered AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY game_date, game_id) AS game_number
    FROM both_sides
)
SELECT *,
       (game_number - 1) / 10 + 1 AS grid_row,   -- whole-number division: games 1-10 are row 1, 11-20 row 2, ...
       (game_number - 1) % 10 + 1 AS grid_col,   -- % is the remainder: position 1 to 10 within the row
       game_id || '-' || team_id  AS team_game_key
FROM numbered;


-- 4. Game Score for every player-game, plus its percentile.
-- Game Score is calculated here, not stored. The percentile compares each game against
-- every player-game in the season with 5 or more minutes (the "pool").
-- PERCENT_RANK gives 0 to 1: 0.99 means better than 99% of the pool.
-- Games under 5 minutes get no percentile (NULL), so they don't distort the scale.
CREATE OR REPLACE VIEW player_game_scores AS
WITH scored AS (
    SELECT game_id,
           player_id,
           team_id,
           min,
           pts + 0.4 * fgm - 0.7 * fga - 0.4 * (fta - ftm)
               + 0.7 * oreb + 0.3 * dreb + stl + 0.7 * ast + 0.7 * blk
               - 0.4 * pf - tov AS game_score
    FROM player_game_stats
),
pool AS (
    SELECT game_id,
           player_id,
           PERCENT_RANK() OVER (ORDER BY game_score) AS game_score_pct
    FROM scored
    WHERE min >= 5
)
SELECT s.game_id,
       s.player_id,
       s.team_id,
       s.game_score,
       pool.game_score_pct
FROM scored s
LEFT JOIN pool ON pool.game_id = s.game_id AND pool.player_id = s.player_id;

-- 5. Standings: one row per team, ranked against all 30 teams together and within its conference.
-- Ranked by wins, then total point differential to break ties.
CREATE OR REPLACE VIEW team_standings AS
SELECT t.team_id,
       t.full_name,
       t.abbreviation,
       t.conference,
       COUNT(*)                                          AS games,
       SUM(CASE WHEN tg.won THEN 1 ELSE 0 END)           AS wins,
       SUM(CASE WHEN tg.won THEN 0 ELSE 1 END)           AS losses,
       ROUND(AVG(tg.won::int), 3)                        AS win_pct,
       SUM(tg.point_diff)                                AS total_point_diff,
       ROUND(AVG(tg.point_diff), 1)                      AS avg_point_diff,
       RANK() OVER (ORDER BY SUM(CASE WHEN tg.won THEN 1 ELSE 0 END) DESC,
                             SUM(tg.point_diff) DESC)    AS league_rank,
       RANK() OVER (PARTITION BY t.conference
                    ORDER BY SUM(CASE WHEN tg.won THEN 1 ELSE 0 END) DESC,
                             SUM(tg.point_diff) DESC)    AS conference_rank,
       'https://cdn.nba.com/logos/nba/' || t.team_id || '/global/L/logo.svg' AS logo_url
FROM teams t
JOIN team_games tg ON tg.team_id = t.team_id
GROUP BY t.team_id, t.full_name, t.abbreviation, t.conference;

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
       SUM(pgs.min)                                                   AS total_min,
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
       ROUND(100.0 * SUM(pgs.ftm)  / NULLIF(SUM(pgs.fta), 0), 1)      AS ft_pct,
       ROUND(AVG(gs.game_score), 1)                                   AS avg_game_score,
       'https://cdn.nba.com/headshots/nba/latest/260x190/' || pgs.player_id || '.png' AS headshot_url
FROM player_game_stats pgs
JOIN players p ON p.player_id = pgs.player_id
JOIN player_game_scores gs ON gs.game_id = pgs.game_id AND gs.player_id = pgs.player_id
GROUP BY pgs.team_id, pgs.player_id, p.player_name;


-- 7. One row per player per game on his team's schedule, with NULLs for games he missed.
-- Used for the player page heatmap and stat cards. A traded player gets a set of rows for each team.
CREATE OR REPLACE VIEW player_games AS
WITH roster AS (
    SELECT DISTINCT team_id, player_id FROM player_game_stats
)
SELECT r.team_id,
       r.player_id,
       p.player_name,
       tg.game_id,
       tg.game_number,
       tg.grid_row,
       tg.grid_col,
       tg.game_date,
       tg.opponent_id,
       tg.is_home,
       tg.pts_for,
       tg.pts_against,
       tg.won,
       (pgs.game_id IS NOT NULL)      AS played,
       pgs.min,
       pgs.pts,
       pgs.oreb + pgs.dreb            AS reb,
       pgs.ast, pgs.stl, pgs.blk, pgs.tov,
       pgs.fgm, pgs.fga, pgs.fg3m, pgs.fg3a, pgs.ftm, pgs.fta,
       pgs.plus_minus,
       gs.game_score,
       gs.game_score_pct,
       tg.game_id || '-' || r.team_id || '-' || r.player_id AS player_game_key,
       r.team_id || '-' || r.player_id                      AS team_player_key,
        tg.game_id || '-' || r.team_id AS team_game_key,
       'https://cdn.nba.com/headshots/nba/latest/260x190/' || r.player_id || '.png' AS headshot_url
FROM roster r
JOIN players p     ON p.player_id = r.player_id
JOIN team_games tg ON tg.team_id = r.team_id
LEFT JOIN player_game_stats pgs
       ON pgs.game_id = tg.game_id AND pgs.player_id = r.player_id AND pgs.team_id = r.team_id
LEFT JOIN player_game_scores gs
       ON gs.game_id = pgs.game_id AND gs.player_id = pgs.player_id;

-- 8. One row per shot, with a text label and the game-clock order for the shot chart.
-- action_type and short_name are added last so the view can be rebuilt (new columns go at the end).
CREATE OR REPLACE VIEW shot_events AS
SELECT s.game_id,
       s.game_event_id,
       s.player_id,
       p.player_name,
       s.team_id,
       s.loc_x,
       s.loc_y,
       s.game_id || '-' || s.team_id                       AS team_game_key,
       s.game_id || '-' || s.team_id || '-' || s.player_id AS player_game_key,
       CASE WHEN s.shot_made_flag = 1 THEN 'Made' ELSE 'Missed' END AS result,
       CASE WHEN s.shot_type LIKE '3PT%' THEN 3 ELSE 2 END          AS shot_value,
       s.shot_distance,
       s.shot_zone_basic,
       s.shot_zone_area,
       s.shot_zone_range,
       CASE WHEN s.period <= 4 THEN 'Q' || s.period ELSE 'OT' || (s.period - 4) END
         || ' ' || s.minutes_remaining || ':' || LPAD(s.seconds_remaining::text, 2, '0') AS game_clock,
       s.period * 10000 - (s.minutes_remaining * 60 + s.seconds_remaining)             AS shot_order,
       CASE WHEN s.period <= 4 THEN 'Q' || s.period ELSE 'OT' || (s.period - 4) END
         || ' ' || s.minutes_remaining || ':' || LPAD(s.seconds_remaining::text, 2, '0')
         || '  ' || s.shot_distance || ' ft ' || s.action_type
         || CASE WHEN s.shot_type LIKE '3PT%' THEN ' (3PT)' ELSE ' (2PT)' END          AS shot_label,
       s.action_type,
       LEFT(p.player_name, 1) || '. ' || SUBSTRING(p.player_name FROM POSITION(' ' IN p.player_name) + 1) AS short_name
FROM shots s
JOIN players p ON p.player_id = s.player_id;