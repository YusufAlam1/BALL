-- Find if an injury is a repeat
-- if a player had an injury once in a given body region AND
-- then that same body region again gets injured, the increment this column by one

WITH region_count AS (
    SELECT player_id,
        injury_date,
        return_status,
        diagnosis,
        body_region,
        COUNT(body_region) OVER (
            PARTITION BY player_id, body_region 
            ORDER BY injury_date
        ) AS injury_count
    FROM injuries
    WHERE 
        body_region IS NOT NULL AND 
        player_id IS NOT NULL
)
-- , repeat_determine AS (
SELECT *,
    full_name,
    CASE
    WHEN injury_count = 1 THEN 'N'
    WHEN injury_count > 1 THEN 'Y'
    END AS is_repeat
FROM region_count r
JOIN players p ON p.player_id = r.player_id ;
-- ) 
-- SELECT *
-- FROM repeat_determine
-- WHERE is_repeat = 'Y';