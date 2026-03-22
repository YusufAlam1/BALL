-- Base game-level data with all features for injury prediction v2.
-- Used to build X-day lookback features and Y-day forward targets in Python.
-- Joins: player_game_stats, anthro, players, game_dates, game_stats_advanced.
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
WHERE g.speed != 0 AND g.distance != 0;
