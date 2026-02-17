-- Player-specific games for lookback window.
-- Parameters: :player_id, :lookback_days
-- Returns games within the last lookback_days (from player's most recent game) for the given player.
-- Note: Parameters are passed from Python - use ? placeholders for sqlite3.
WITH player_max_date AS (
    SELECT MAX(gd.game_date) AS max_date
    FROM player_game_stats g
    JOIN game_dates gd ON gd.game_id = g.game_id
    WHERE g.player_id = ? AND g.speed != 0 AND g.distance != 0
)
SELECT
    g.player_id,
    p.full_name,
    gd.game_date,
    g.game_id,
    CAST(strftime('%Y', gd.game_date) AS INT) - CAST(strftime('%Y', p.birthdate) AS INT) AS age,
    g.speed,
    g.distance,
    a.HEIGHT_WO_SHOES AS height_wo_shoes,
    a.WEIGHT AS weight,
    a.WINGSPAN AS wingspan,
    a.STANDING_REACH AS standing_reach,
    a.BODY_FAT_PCT AS body_fat_pct,
    a.HAND_LENGTH AS hand_length,
    a.HAND_WIDTH AS hand_width,
    gsa."minutes" AS minutes,
    gsa.usagePercentage,
    gsa.pace,
    gsa.possessions
FROM player_game_stats g
JOIN anthro a ON a.PLAYER_ID = g.player_id
JOIN players p ON p.id = g.player_id
JOIN game_dates gd ON gd.game_id = g.game_id
JOIN game_stats_advanced gsa ON gsa.gameId = g.game_id AND gsa.personId = g.player_id
CROSS JOIN player_max_date pmd
WHERE g.player_id = ?
  AND g.speed != 0 AND g.distance != 0
  AND gd.game_date >= date(pmd.max_date, '-' || ? || ' days')
ORDER BY gd.game_date DESC;
