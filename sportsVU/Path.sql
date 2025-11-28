-- Getting the Necessary Data for the physical path on the court of Kevin Durant's Injury
SELECT x_loc, y_loc, game_clock
FROM GPS
WHERE player_id = 201142 AND game_clock BETWEEN 209 AND 216 ;