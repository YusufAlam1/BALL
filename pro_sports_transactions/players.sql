-- Get a list of all the players in the prosportstrasactions db (NBA_injuries.db)
SELECT DISTINCT(relinquished) AS player
FROM NBA_injuries
WHERE relinquished NOT LIKE ' placed on%' 
    -- OR relinquished NOT LIKE '%(DTD)%'
UNION
SELECT DISTINCT(acquired) AS player
FROM NBA_injuries
WHERE acquired NOT LIKE ' placed on%' 
    -- OR acquired NOT LIKE '%(DTD)%'
ORDER BY player;