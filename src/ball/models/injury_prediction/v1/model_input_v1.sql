SELECT 
    a.player_id,
    strftime('%Y', gd.game_date) - strftime('%Y', birthdate) as age,
    g.game_id, 
    speed, 
    distance,
    height_wo_shoes,
    "weight",
    wingspan,
    standing_reach,
    body_fat_pct,
    hand_length,
    hand_width,
    CASE WHEN (g.game_id, a.player_id) NOT IN (
        SELECT 
            g.game_id,
            a.player_id
        FROM player_game_stats g
        JOIN anthro a ON a.player_id = g.player_id
        JOIN players p ON p.id = g.player_id
        JOIN game_dates gd ON gd.game_id = g.game_id
        JOIN (
            SELECT
                player_id,
                gd.game_id, 
                game_date,
                LAG(game_date) OVER (
                    PARTITION BY player_id
                    ORDER BY game_date
                ) AS game_before
            FROM game_dates gd
            JOIN player_game_stats pgs ON pgs.game_id = gd.game_id
            JOIN players p ON p.id = pgs.player_id
        ) AS ld ON ld.game_id = g.game_id 
            AND ld.player_id = g.player_id
        JOIN injuries i ON i.injury_date BETWEEN ld.game_before AND gd.game_date
            AND i.player_id = g.player_id
        WHERE speed != 0 
            AND distance != 0
            AND relinquished LIKE "TRUE"
    ) THEN 0 ELSE 1 END AS is_injured
FROM player_game_stats g
JOIN anthro a ON a.player_id = g.player_id
JOIN players p ON p.id = g.player_id
JOIN game_dates gd ON gd.game_id = g.game_id
WHERE speed != 0 AND distance != 0;