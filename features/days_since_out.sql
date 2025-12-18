WITH events AS (
  SELECT
    "injury_id",
    DATE("Date") AS "Date",
    "Team",
    player_name,
    COALESCE(NULLIF(TRIM("Acquired"), ''), NULLIF(TRIM("Relinquished"), '')) AS player,
    player_id,
    CASE
      WHEN "Relinquished" IS NOT NULL AND TRIM("Relinquished") != '' THEN 'out'
      WHEN "Acquired" IS NOT NULL AND TRIM("Acquired") != '' THEN 'in'
    END AS event_type
  FROM injury_list
  WHERE ("Acquired" IS NOT NULL AND TRIM("Acquired") != '')
     OR ("Relinquished" IS NOT NULL AND TRIM("Relinquished") != '')
),
ordered AS (
  SELECT
    *,
    LEAD(event_type) OVER (PARTITION BY player ORDER BY "Date", "injury_id") AS next_event,
    LEAD("Date") OVER (PARTITION BY player ORDER BY "Date", "injury_id") AS next_date
  FROM events
),
durations AS (
    SELECT
    player_id,
    player,
    player_name,
    "Date" AS out_date,
    next_date  AS in_date,

    CAST(julianday(next_date) - julianday("Date") AS INT) AS days_out
    FROM ordered
    WHERE event_type = 'out' AND next_event = 'in'
),
max_dates AS (
  SELECT player_id, 
    player_name, 
    MAX(out_date) AS last_out
  FROM durations
  GROUP BY player_id
)
SELECT m.*,
  p.is_active,
  julianday('2023-04-10') - julianday(last_out) AS days_since_out
FROM max_dates m
JOIN players p ON p.id = m.player_id
WHERE is_active = 'True'
ORDER BY last_out DESC;
