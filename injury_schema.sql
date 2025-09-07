CREATE TABLE injuries (
    player_age INTEGER,
    player_weight REAL,
    player_height REAL,
    previous_injuries INTEGER,
    training_intensity REAL,
    recovery_time INTEGER,
    likelihood_of_injury INTEGER
);

ALTER TABLE injuries ADD COLUMN id INTEGER;
UPDATE injuries SET id = rowid;