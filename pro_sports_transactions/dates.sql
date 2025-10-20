WITH events AS (
  SELECT
    "injury_id",
    DATE("Date") AS "Date",
    "Team",
    COALESCE(NULLIF(TRIM("Acquired"), ''), NULLIF(TRIM("Relinquished"), '')) AS player,
    CASE
      WHEN "Relinquished" IS NOT NULL AND TRIM("Relinquished") != '' THEN 'out'
      WHEN "Acquired" IS NOT NULL AND TRIM("Acquired") != '' THEN 'in'
    END AS event_type
  FROM NBA_injuries
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
    player,
    "Date" AS out_date,
    next_date  AS in_date,

    CAST(julianday(next_date) - julianday("Date") AS INT) AS days_out
    FROM ordered
    WHERE event_type = 'out' AND next_event = 'in'
)
SELECT player, SUM(days_out) AS total_days_out
FROM durations
WHERE player LIKE {user_player_input}
GROUP BY player;