-- Rolling speed of a player based on GPS data
-- Takes the rolling speed of each player over a 1 second (30 frame) window
-- Using simple delta distance / delta time calculation
-- With delta being change in a variable -> (d2 - d1) / (t2 - t1)
-- Distance is calculated using Euclidean distance between x_loc and y_loc

-- A problem with the data is that there are sometimes time gaps
-- This leads the DELTA t value to be skewed, which is why you get insane speeds
-- TO fix this we can either ignore these, or restructure the gps game_clock column

-- Additionaly SQLite doesn't suport exponents, so the speed is a pseudo measurement of (km^2 / h^2)
-- To fix this, when we run it in python, sqrt the column


WITH end_start AS (
    SELECT
        g.player_id,
        p.full_name,
        g.event_id,
        g.game_clock AS t1,
        g.x_loc AS x1,
        g.y_loc AS y1,
        LAG(g.x_loc) OVER (PARTITION BY g.player_id ORDER BY g.event_id, g.game_clock DESC) AS x2,
        LAG(g.y_loc) OVER (PARTITION BY g.player_id ORDER BY g.event_id, g.game_clock DESC) AS y2,
        LAG(g.game_clock) OVER (PARTITION BY g.player_id ORDER BY g.event_id, g.game_clock DESC) AS t2
    FROM GPS g
    JOIN players p ON p.id = g.player_id
)
,
speed AS (
    SELECT *,
            (((x2 - x1)*(x2 - x1)) + ((y2 - y1)*(y2 - y1))) / ((t2 - t1)*(t2 - t1)) * (0.0003048 * 0.0003048) * (3600 * 3600)
    AS "delta_v_sq_(km2_per_h2)"
    FROM end_start
)
-- SELECT player_id,
--     full_name,
--     AVG("delta_v_sq_(km2_per_h2)") AS "average_speed_(km^2/h^2)"

SELECT *,
    AVG("delta_v_sq_(km2_per_h2)") OVER(
        PARTITION BY player_id 
        ORDER By event_id, t1 DESC 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS "average_speed_(km^2/h^2)"
FROM speed  ;
-- GROUP BY player_id;