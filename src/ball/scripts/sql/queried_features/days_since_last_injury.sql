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
max_dates AS (
  SELECT
    player_id,
    MAX(injury_date) AS last_out
  FROM ordered
  WHERE event_type = 'out'
  GROUP BY player_id
)
-- SELECT * FROM ordered;
SELECT
  m.*,
  p.is_active,
  (CAST('2023-04-17' AS DATE) - m.last_out) AS days_since_out
FROM max_dates m
JOIN players p
  ON p.player_id = m.player_id
WHERE p.is_active = TRUE
ORDER BY m.last_out DESC;