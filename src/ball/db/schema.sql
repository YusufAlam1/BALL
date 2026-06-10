CREATE TABLE anthro (
    player_id INTEGER PRIMARY KEY,
    player_name TEXT,
    height REAL,
    weight REAL,
    birth_date DATE,
    college TEXT,
    country TEXT
)

CREATE TABLE injury_list (
    injury_id INTEGER PRIMARY KEY,
    Date DATE,
    Team TEXT,
    Acquired TEXT,
    Relinquished TEXT,
    Notes TEXT,
    player_name TEXT,
    player_id REAL,
    body_region TEXT
)

CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    full_name TEXT,
    first_name TEXT,
    last_name TEXT,
    is_active BOOLEAN
)

CREATE TABLE GPS (
    team_id INTEGER,
    player_id INTEGER,
    x_loc REAL,
    y_loc REAL,
    radius REAL,
    game_clock REAL,
    shot_clock REAL,
    quarter INTEGER,
    game_id TEXT,
    event_id INTEGER
)