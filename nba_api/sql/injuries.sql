-- Through Efficient Mapping Only 100 / 2800 names are left NULL
-- (most of these players being too old to collect data from anyway)
SELECT DISTINCT(i.player_name), p.full_name 
FROM injury_list i
LEFT JOIN players p ON p.id = i.player_id
WHERE p.full_name IS NULL;