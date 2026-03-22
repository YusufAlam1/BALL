-- Injury dates per player (relinquished = out of lineup).
-- Used to compute Y-day forward targets.
SELECT
    player_id,
    injury_date,
    relinquished
FROM injuries
WHERE UPPER(CAST(relinquished AS TEXT)) = 'TRUE';
