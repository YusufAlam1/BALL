WITH events AS (
  SELECT
    injury_id,
    injury_date,
    team_id,
    player_id,
    CASE
      WHEN relinquished = TRUE THEN 'out'
      WHEN acquired = TRUE THEN 'in'
    END AS event_type
  FROM injuries
  WHERE acquired = TRUE
     OR relinquished = TRUE
),
ordered AS (  
  SELECT
    *,
    LEAD(event_type) OVER (
      PARTITION BY player_id 
      ORDER BY injury_date, injury_id
    ) AS next_event,
    LEAD(injury_date) OVER (
      PARTITION BY player_id 
      ORDER BY injury_date, injury_id
    ) AS next_date
  FROM events
),
durations AS (
    SELECT
    player_id,
    injury_date AS out_date,
    next_date  AS in_date,
    (next_date - injury_date) AS days_out
    FROM ordered
    WHERE event_type = 'out' AND next_event = 'in'
)
SELECT *,
    SUM(days_out) AS total_days_out,
    COUNT(1) AS total_injuries
FROM durations
GROUP BY player_id;
-- ORDER BY CAST(player_id AS INT);