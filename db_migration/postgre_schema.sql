CREATE TABLE players (
    player_id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE anthro (
    player_id INTEGER PRIMARY KEY REFERENCES players(player_id) ON DELETE CASCADE,  -- Primary key ensures 1-to-1 correspondence where 1 player has exactly 1 row in players and anthro
    height_w_o_shoes REAL,
    height_w_o_shoes_ft_in TEXT,
    height_w_shoes REAL,
    height_w_shoes_ft_in TEXT,
    weight REAL,
    wingspan REAL,
    wingspan_ft_in TEXT,
    standing_reach REAL,
    standing_reach_ft_in TEXT,
    body_fat_pct REAL,
    hand_length REAL,
    hand_width REAL
);

CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    abbreviation TEXT,
    nickname TEXT,
    city TEXT,
    state TEXT
);

CREATE TABLE injuries (
    injury_id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(player_id),
    team_id INTEGER REFERENCES teams(team_id),
    injury_date DATE,
    acquired BOOLEAN,
    relinquished BOOLEAN,
    body_part TEXT,
    diagnosis TEXT,
    return_status TEXT,
    notes TEXT
);

CREATE TABLE player_game_stats (
    game_id INTEGER,
    team_id INTEGER REFERENCES teams(team_id),
    player_id INTEGER REFERENCES players(player_id),
    team_abbreviation TEXT,
    team_city TEXT,
    player_name TEXT,
    start_position TEXT,
    comment TEXT,
    min TIME,
    fgm INTEGER,
    fga INTEGER,
    fg_pct REAL,
    fg3m INTEGER,
    fg3a INTEGER,
    fg3_pct REAL,
    ftm INTEGER,
    fta INTEGER,
    ft_pct REAL,
    oreb INTEGER,
    dreb INTEGER,
    reb INTEGER,
    ast INTEGER,
    stl INTEGER,
    blk INTEGER,
    turnovers INTEGER,      -- Having this as "to" is problematic since it's a reserved word in SQL
    pf INTEGER,
    pts INTEGER,
    plus_minus INTEGER,
    PRIMARY KEY (game_id, player_id)
);

CREATE TABLE sportsvu (
    PRIMARY KEY (game_id, event_id, player_id),      -- Primary key composed of several unique indetifying columns
    team_id INTEGER REFERENCES teams(team_id),
    player_id INTEGER REFERENCES players(player_id),
    x_loc REAL,
    y_loc REAL,
    radius REAL,
    game_clock TIME,
    shot_clock TIME,
    quarter INTEGER,
    game_date DATE,
    game_id INTEGER,
    event_id INTEGER
);

CREATE TABLE pbp (
    game_id INTEGER,
    event_id INTEGER,
    player_id INTEGER REFERENCES players(player_id),
    team_id INTEGER REFERENCES teams(team_id),
    game_date TIMESTAMP,
    event_time TIME,
    event_type TEXT,
    description TEXT,
    home_score INTEGER,
    away_score INTEGER,
    PRIMARY KEY (game_id, event_id)
);