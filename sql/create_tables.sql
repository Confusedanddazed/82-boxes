-- create_tables.sql
-- Creates the five tables for 82 Boxes. Run it in the boxes82 database.
-- Tables are created parents first (teams, players, games), then the tables that point to them.

-- Wipes the tables if they already exist, so this file can be rerun from scratch.
-- (Careful: once data is loaded, running this deletes it.)
DROP TABLE IF EXISTS shots, player_game_stats, games, players, teams;

CREATE TABLE teams (
    team_id       INTEGER      PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    abbreviation  VARCHAR(5)   NOT NULL UNIQUE,
    city          VARCHAR(100) NOT NULL,
    nickname      VARCHAR(100) NOT NULL
);

CREATE TABLE players (
    player_id    INTEGER      PRIMARY KEY,
    player_name  VARCHAR(100) NOT NULL
);

CREATE TABLE games (
    game_id       VARCHAR(10) PRIMARY KEY,   -- text, because of the leading zeros (0022501192)
    season        INTEGER     NOT NULL,      -- 2025 means the 2025-26 season
    game_type     VARCHAR(20) NOT NULL,
    game_date     DATE        NOT NULL,
    home_team_id  INTEGER     NOT NULL REFERENCES teams (team_id),
    away_team_id  INTEGER     NOT NULL REFERENCES teams (team_id),
    neutral_site  BOOLEAN     NOT NULL,
    CHECK (home_team_id <> away_team_id)     -- a team can't play itself
);

CREATE TABLE player_game_stats (
    game_id     VARCHAR(10)  NOT NULL REFERENCES games (game_id),
    player_id   INTEGER      NOT NULL REFERENCES players (player_id),
    team_id     INTEGER      NOT NULL REFERENCES teams (team_id),
    min         NUMERIC(6,2) NOT NULL,
    pts         INTEGER      NOT NULL,
    fgm         INTEGER      NOT NULL,
    fga         INTEGER      NOT NULL,
    fg3m        INTEGER      NOT NULL,
    fg3a        INTEGER      NOT NULL,
    ftm         INTEGER      NOT NULL,
    fta         INTEGER      NOT NULL,
    oreb        INTEGER      NOT NULL,
    dreb        INTEGER      NOT NULL,
    ast         INTEGER      NOT NULL,
    stl         INTEGER      NOT NULL,
    blk         INTEGER      NOT NULL,
    tov         INTEGER      NOT NULL,
    pf          INTEGER      NOT NULL,
    plus_minus  INTEGER      NOT NULL,       -- the only stat that can be negative
    PRIMARY KEY (game_id, player_id),        -- one row per player per game
    CHECK (min >= 0 AND pts >= 0 AND fgm >= 0 AND fga >= 0 AND fg3m >= 0 AND fg3a >= 0
           AND ftm >= 0 AND fta >= 0 AND oreb >= 0 AND dreb >= 0 AND ast >= 0
           AND stl >= 0 AND blk >= 0 AND tov >= 0 AND pf >= 0),
    CHECK (fgm <= fga AND fg3m <= fg3a AND ftm <= fta AND fg3m <= fgm)  -- can't make more than you take
);

CREATE TABLE shots (
    game_id            VARCHAR(10)  NOT NULL REFERENCES games (game_id),
    game_event_id      INTEGER      NOT NULL,
    player_id          INTEGER      NOT NULL REFERENCES players (player_id),
    team_id            INTEGER      NOT NULL REFERENCES teams (team_id),
    period             INTEGER      NOT NULL,
    minutes_remaining  INTEGER      NOT NULL,
    seconds_remaining  INTEGER      NOT NULL,
    action_type        VARCHAR(100) NOT NULL,
    shot_type          VARCHAR(30)  NOT NULL,
    shot_zone_basic    VARCHAR(50)  NOT NULL,
    shot_zone_area     VARCHAR(50)  NOT NULL,
    shot_zone_range    VARCHAR(50)  NOT NULL,
    shot_distance      INTEGER      NOT NULL,
    loc_x              INTEGER      NOT NULL,
    loc_y              INTEGER      NOT NULL,
    shot_made_flag     INTEGER      NOT NULL CHECK (shot_made_flag IN (0, 1)),  -- 1 = made, 0 = missed
    PRIMARY KEY (game_id, game_event_id)
);

-- Indexes make the lookups the app will do often (a player's games, a team's games,
-- a date range) fast. The primary keys already get an index automatically.
CREATE INDEX idx_games_date          ON games (game_date);
CREATE INDEX idx_games_home_team     ON games (home_team_id);
CREATE INDEX idx_games_away_team     ON games (away_team_id);
CREATE INDEX idx_pgs_player          ON player_game_stats (player_id);
CREATE INDEX idx_pgs_team            ON player_game_stats (team_id);
CREATE INDEX idx_shots_player        ON shots (player_id);
CREATE INDEX idx_shots_team          ON shots (team_id);