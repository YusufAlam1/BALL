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
    "minutes",
    usagePercentage,
    pace,
    possessions,
    CASE WHEN (g.game_id, a.player_id) IN (
        SELECT
            ld.game_id_before,
            ld.player_id
        FROM (
            SELECT
                player_id,
                gd.game_id,
                game_date,
                LAG(game_date) OVER (
                    PARTITION BY player_id
                    ORDER BY game_date
                ) AS game_before,
                LAG(gd.game_id) OVER (
                    PARTITION BY player_id
                    ORDER BY game_date
                ) AS game_id_before
            FROM game_dates gd
            JOIN player_game_stats pgs ON pgs.game_id = gd.game_id
            JOIN players p ON p.id = pgs.player_id
            WHERE pgs.speed != 0 AND pgs.distance != 0
        ) AS ld
        JOIN injuries i ON i.player_id = ld.player_id
            AND i.relinquished LIKE 'TRUE'
            AND i.injury_date BETWEEN ld.game_before AND ld.game_date
        WHERE ld.game_id_before IS NOT NULL
    ) THEN 1 ELSE 0 END AS is_injured
FROM player_game_stats g
JOIN anthro a ON a.player_id = g.player_id
JOIN players p ON p.id = g.player_id
JOIN game_dates gd ON gd.game_id = g.game_id
JOIN game_stats_advanced gsa ON gsa.gameid = g.game_id 
    AND gsa.personId = g.player_id
WHERE speed != 0 AND distance != 0;