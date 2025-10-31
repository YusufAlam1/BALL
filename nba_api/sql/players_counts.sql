-- There are 5024 players in the nba_api players table
SELECT id, full_name
FROM players
ORDER by full_name;

-- There are 2795 Distinct players from the prosports transaction data
SELECT *
FROM injured_players inj
LEFT JOIN id_players idp ON inj.name = idp.name;

-- There are 356 players in prosports that could'nt automatically be mapped to an nba_api player id
SELECT name
FROM injured_players
WHERE name NOT IN (
    SELECT inj.name
    FROM id_players idp
    LEFT JOIN injured_players inj ON idp.name = inj.name
    WHERE inj.name IS NOT NULL
);