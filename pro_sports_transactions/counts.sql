SELECT
  (SELECT COUNT(*) FROM NBA_Injuries WHERE Acquired != '') AS acquired_count,
  (SELECT COUNT(*) FROM NBA_Injuries WHERE Relinquished != '') AS relinquished_count,
  (SELECT COUNT(*) FROM NBA_Injuries) AS total_transactions,
  (
    (SELECT COUNT(DISTINCT Acquired)
    FROM NBA_injuries
    WHERE Acquired != '') 
    +
    (SELECT COUNT(DISTINCT Relinquished)
      FROM NBA_injuries
      WHERE Relinquished != ''
        AND Relinquished NOT IN (
            SELECT DISTINCT Acquired
            FROM NBA_injuries
            WHERE Acquired != ''
        )
    )
  ) AS total_unique_teams;