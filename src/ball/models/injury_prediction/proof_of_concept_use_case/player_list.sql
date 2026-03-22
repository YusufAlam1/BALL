-- All players with game stats (for fuzzy name search).
SELECT DISTINCT
    p.id AS player_id,
    p.full_name
FROM players p
JOIN player_game_stats g ON g.player_id = p.id
JOIN game_dates gd ON gd.game_id = g.game_id
WHERE g.speed != 0 AND g.distance != 0
ORDER BY p.full_name;
