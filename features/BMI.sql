SELECT p.player_id,
    full_name,
    ROUND(
    ((weight * 0.453592) /
     (height_wo_shoes * 0.0254 * height_wo_shoes * 0.0254))::numeric,
    2
  ) AS bmi
FROM anthro a
JOIN players p ON a.player_id = p.player_id;;