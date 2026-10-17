# 82 Boxes ERD 
Diagram's types are general, exact SQL types are in sql/create_tables.sql.
```mermaid
erDiagram
  TEAMS ||--o{ GAMES : home
  TEAMS ||--o{ GAMES : away
  TEAMS ||--o{ PLAYER_GAME_STATS : "played for"
  GAMES ||--o{ PLAYER_GAME_STATS : has
  PLAYERS ||--o{ PLAYER_GAME_STATS : records
  GAMES ||--o{ SHOTS : has
  PLAYERS ||--o{ SHOTS : takes
  TEAMS ||--o{ SHOTS : "taken for"
  TEAMS {
    int team_id PK
    string full_name
    string abbreviation
    string city
    string nickname
    string conference
  }
  PLAYERS {
    int player_id PK
    string player_name
  }
  GAMES {
    string game_id PK
    int season
    string game_type
    date game_date
    int home_team_id FK
    int away_team_id FK
    boolean neutral_site
  }
  PLAYER_GAME_STATS {
    string game_id PK
    int player_id PK
    int team_id FK
    numeric min
    int pts
    int fgm
    int fga
    int fg3m
    int fg3a
    int ftm
    int fta
    int oreb
    int dreb
    int ast
    int stl
    int blk
    int tov
    int pf
    int plus_minus
  }
  SHOTS {
    string game_id PK
    int game_event_id PK
    int player_id FK
    int team_id FK
    int period
    int minutes_remaining
    int seconds_remaining
    string action_type
    string shot_type
    string shot_zone_basic
    string shot_zone_area
    string shot_zone_range
    int shot_distance
    int loc_x
    int loc_y
    int shot_made_flag
  }
```


Dashboard schema

```mermaid
erDiagram
  PLAYERS ||--o{ PLAYER_GAMES : player_id
  PLAYERS ||--o{ SHOT_EVENTS : player_id
  TEAM_GAMES ||--o{ PLAYER_GAMES : team_game_key
  PLAYERS {
    int player_id PK
    string player_name
    string headshot_url
    int PPG_Rank "calculated"
    int RPG_Rank "calculated"
    int APG_Rank "calculated"
  }
  PLAYER_B {
    int player_id
    string player_name
    string headshot_url
    int PPG_Rank "calculated"
    int RPG_Rank "calculated"
    int APG_Rank "calculated"
  }
  PLAYER_GAMES {
    int player_id FK
    string team_game_key FK
    string player_name
    bool played
    numeric min
    int pts
    int reb
    int ast
    int stl
    int blk
    int tov
    int fgm
    int fga
    int fg3m
    int fg3a
    int ftm
    int fta
    int plus_minus
    numeric game_score
    numeric game_score_pct
  }
  TEAM_GAMES {
    string team_game_key PK
    string game_id
    date game_date
    int team_id
    int opponent_id
    bool is_home
    int pts_for
    int pts_against
    bool won
    int game_number
    string opponent_logo "calculated"
    string opponent "calculated"
  }
  SHOT_EVENTS {
    string game_id
    int game_event_id
    int player_id FK
    string player_name
    int team_id
    int home_team_id
    int loc_x
    int loc_y
    string result
    string shot_label
  }
  TEAM_STANDINGS {
    int team_id PK
    string full_name
    string abbreviation
    string conference
    int wins
    int losses
    int conference_rank
    string logo_url
  }
  STAT_PICKER {
    string Stat
  }
```