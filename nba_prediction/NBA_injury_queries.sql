WITH counts AS (
  SELECT
    SUM(CASE WHEN NULLIF(Acquired,'')     IS NOT NULL THEN 1 ELSE 0 END) AS acquired_count,
    SUM(CASE WHEN NULLIF(Relinquished,'') IS NOT NULL THEN 1 ELSE 0 END) AS relinquished_count
  FROM NBA_injuries
),
distinct_players AS (
  SELECT COUNT(DISTINCT("name")) AS total_distinct_players
  FROM (
    SELECT NULLIF(Acquired,'')     AS "name"
    FROM NBA_injuries
    UNION ALL
    SELECT NULLIF(Relinquished,'') AS "name"
    FROM NBA_injuries
  ) x
  WHERE "name" IS NOT NULL
)
SELECT
  c.acquired_count,
  c.relinquished_count,
  c.acquired_count + c.relinquished_count AS total_entries,
  d.total_distinct_players
FROM counts c
CROSS JOIN distinct_players d;