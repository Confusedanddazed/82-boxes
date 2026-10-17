-- views.sql (head 2 head)
-- The six views Power BI imports. A view is a saved query: it stores no data
-- and runs again every time Power BI refreshes.
 
-- Delete the old views first so this file can be run again.
DROP VIEW IF EXISTS shot_events, player_games, team_standings,
                    player_game_scores, team_games, player_dim;
 
 
-- 1. team_games: one row per team per game.
--    Team points are the sum of each team's player points.
--    Joining team_pts to itself gives the opponent's points.
CREATE VIEW team_games AS
WITH team_pts AS (
    SELECT game_id, team_id, SUM(pts) AS pts
    FROM player_game_stats
    GROUP BY game_id, team_id
)
SELECT t.game_id,
       g.game_date,
       t.team_id,
       o.team_id                    AS opponent_id,
       g.home_team_id = t.team_id   AS is_home,
       t.pts                        AS pts_for,
       o.pts                        AS pts_against,
       t.pts > o.pts                AS won,
       ROW_NUMBER() OVER (PARTITION BY t.team_id    -- ROW_NUMBER numbers each row, PARTITION restarts the count for each team
                          ORDER BY g.game_date, t.game_id) AS game_number,
       t.game_id || '-' || t.team_id AS team_game_key
FROM team_pts t
JOIN team_pts o ON o.game_id = t.game_id AND o.team_id <> t.team_id
JOIN games g    ON g.game_id = t.game_id;
 
 
-- 2. player_game_scores: Game Score and its percentile for every player-game.
--    scored: calculates Game Score.
--    pool: ranks games of 5 or more minutes (0.99 = better than 99% of the league).
CREATE VIEW player_game_scores AS
WITH scored AS (
    SELECT game_id,
           player_id,
           min,
           pts + 0.4 * fgm - 0.7 * fga - 0.4 * (fta - ftm)
               + 0.7 * oreb + 0.3 * dreb + stl + 0.7 * ast + 0.7 * blk
               - 0.4 * pf - tov AS game_score -- Game Score formula 
    FROM player_game_stats
),
pool AS (
    SELECT game_id,
           player_id,
           PERCENT_RANK() OVER (ORDER BY game_score) AS game_score_pct
    FROM scored
    WHERE min >= 5 -- used to control noise
)
SELECT s.game_id,
       s.player_id,
       s.game_score,
       p.game_score_pct
FROM scored s
LEFT JOIN pool p ON p.game_id = s.game_id AND p.player_id = s.player_id;
 
 
-- 3. team_standings: one row per team with its record and conference rank.
--    Ranked by wins, then point differential. This is the seed on the player card.
CREATE VIEW team_standings AS
WITH records AS (
    SELECT team_id,
           SUM(CASE WHEN won THEN 1 ELSE 0 END) AS wins,
           SUM(CASE WHEN won THEN 0 ELSE 1 END) AS losses,
           SUM(pts_for - pts_against)           AS point_diff
    FROM team_games
    GROUP BY team_id
)
SELECT t.team_id,
       t.full_name,
       t.abbreviation,
       t.conference,
       r.wins,
       r.losses,
       RANK() OVER (PARTITION BY t.conference
                    ORDER BY r.wins DESC, r.point_diff DESC) AS conference_rank,
       'https://cdn.nba.com/logos/nba/' || t.team_id || '/global/L/logo.svg' AS logo_url
FROM teams t
JOIN records r ON r.team_id = t.team_id;
 
 
-- 4. player_dim: one row per player, for the slicers and cards.
CREATE VIEW player_dim AS
SELECT player_id,
       player_name,
       'https://cdn.nba.com/headshots/nba/latest/260x190/' || player_id || '.png' AS headshot_url
FROM players;
 
 
-- 5. player_games: one row per player per game on his team's schedule.
--    Grey boxes are missed games. 
--    A traded player gets rows for each team.
--    Date, opponent and result are in team_games, joined by team_game_key.
CREATE VIEW player_games AS
WITH roster AS (
    SELECT DISTINCT team_id, player_id
    FROM player_game_stats
)
SELECT r.player_id,
       p.player_name,
       tg.team_game_key,
       pgs.game_id IS NOT NULL AS played,
       pgs.min,
       pgs.pts,
       pgs.oreb + pgs.dreb     AS reb,
       pgs.ast,
       pgs.stl,
       pgs.blk,
       pgs.tov,
       pgs.fgm,
       pgs.fga,
       pgs.fg3m,
       pgs.fg3a,
       pgs.ftm,
       pgs.fta,
       pgs.plus_minus,
       gs.game_score,
       gs.game_score_pct
FROM roster r
JOIN players p     ON p.player_id = r.player_id
JOIN team_games tg ON tg.team_id = r.team_id
LEFT JOIN player_game_stats pgs
       ON pgs.game_id = tg.game_id
      AND pgs.player_id = r.player_id
      AND pgs.team_id = r.team_id
LEFT JOIN player_game_scores gs
       ON gs.game_id = pgs.game_id
      AND gs.player_id = pgs.player_id;
 
 
-- 6. shot_events: one row per shot, for the shot charts.
--    home_team_id picks which court is drawn behind the shot.
CREATE VIEW shot_events AS
SELECT s.game_id,
       s.game_event_id,
       s.player_id,
       p.player_name,
       s.team_id,
       g.home_team_id,
       s.loc_x,
       s.loc_y,
       CASE WHEN s.shot_made_flag = 1 THEN 'Made' ELSE 'Missed' END AS result,
       CASE WHEN s.period <= 4 THEN 'Q' || s.period ELSE 'OT' || (s.period - 4) END
         || ' ' || s.minutes_remaining || ':' || LPAD(s.seconds_remaining::text, 2, '0')
         || '  ' || s.shot_distance || ' ft ' || s.action_type
         || CASE WHEN s.shot_type LIKE '3PT%' THEN ' (3PT)' ELSE ' (2PT)' END AS shot_label -- hover feature
FROM shots s
JOIN players p ON p.player_id = s.player_id
JOIN games g   ON g.game_id = s.game_id;