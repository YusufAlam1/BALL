WITH events AS (
  SELECT
    "injury_id",
    DATE("Date") AS "Date",
    "Team",
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
    "Date" AS out_date,
    next_date  AS in_date,

    CAST(julianday(next_date) - julianday("Date") AS INT) AS days_out
    FROM ordered
    WHERE event_type = 'out' AND next_event = 'in'
)
SELECT * 
FROM durations
WHERE player LIKE 'LeBron James'