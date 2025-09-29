-- SELECT player_name,
--     age,
--     SUM(Days) AS days_missed 
-- FROM soccer_injuries
-- GROUP BY player_name
-- ORDER BY age

SELECT age,
    ROUND(AVG(Days), 2) AS avg_days_missed
FROM soccer_injuries
GROUP BY age