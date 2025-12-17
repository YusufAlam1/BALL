-- Find if an injury is a repeat
-- if a player had an injury once in a given body region AND
-- then that same body region again gets injured, the increment this column by one

WITH region_count AS (
    SELECT player_id,
        player_name,
        "Date",
        "Status",
        diagnosis,
        body_region,
        COUNT(body_region) OVER (
            PARTITION BY player_id, body_region 
            ORDER BY "date"
        ) AS injury_count
    FROM injury_list
    WHERE 
        body_region IS NOT NULL AND 
        player_id NOT LIKE ''
)
-- , repeat_determine AS (
SELECT *,
    CASE
    WHEN injury_count = 1 THEN 'N'
    WHEN injury_count > 1 THEN 'Y'
    ELSE 0
    END AS is_repeat
FROM region_count
-- )
-- SELECT *
-- FROM repeat_determine
-- WHERE is_repeat = 'Y';