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


-- ==================== POSTGRES / SUPABASE VERSION ====================
-- Translated from injury_list (SQLite) to injuries (Postgres/Supabase)
-- acquired/relinquished are now booleans, player_name comes via JOIN on players

WITH events AS (
  SELECT
    i.injury_id,
    i.injury_date,
    i.team_id,
    p.full_name AS player_name,
    i.player_id,
    CASE
      WHEN i.relinquished = TRUE THEN 'out'
      WHEN i.acquired = TRUE THEN 'in'
    END AS event_type
  FROM injuries i
  JOIN players p ON p.player_id = i.player_id
  WHERE i.acquired = TRUE
     OR i.relinquished = TRUE
),
ordered AS (
  SELECT
    *,
    LEAD(event_type) OVER (PARTITION BY player_id ORDER BY injury_date, injury_id) AS next_event,
    LEAD(injury_date) OVER (PARTITION BY player_id ORDER BY injury_date, injury_id) AS next_date
  FROM events
),
max_dates AS (
  SELECT player_id,
    player_name,
    MAX(next_date) AS return_date,
    injury_date
  FROM ordered
  WHERE injury_date < (SELECT MAX(next_date) FROM ordered)
  GROUP BY player_id, player_name, injury_date
),
min_dates AS (
  SELECT player_id,
    player_name,
    next_date AS return_date,
    injury_date
  FROM ordered
)
-- SELECT * FROM max_dates;
SELECT * FROM ordered;

-- * Use a window function with X preceding to get the last 'out' for a given period of time
