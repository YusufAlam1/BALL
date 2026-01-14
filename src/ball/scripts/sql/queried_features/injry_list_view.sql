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
max_dates AS (
  SELECT player_id, 
    player_name, 
    MAX(next_date) AS return_date,
    ("Date") AS injury_date
  FROM ordered
  WHERE "Date" < (SELECT MAX(next_date) FROM ordered)
  GROUP BY player_id
),
min_dates AS (
  SELECT player_id, 
    player_name, 
    (next_date) AS return_date,
    ("Date") AS injury_date
  FROM ordered
)
-- SELECT * FROM max_dates;
SELECT * FROM ordered;


-- * Use a windpw function with X preceeding to get the last 'out' for a given period of time
