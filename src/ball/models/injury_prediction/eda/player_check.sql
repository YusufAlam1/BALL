SELECT g.game_date, 
    speed, 
    distance, 
    is_injured
FROM model_v4
JOIN game_dates g ON model_v4.game_id = g.game_id
WHERE player_id = (
    SELECT id
    FROM players
    WHERE full_name LIKE 'Kyrie Irving'
)
ORDER BY g.game_date;