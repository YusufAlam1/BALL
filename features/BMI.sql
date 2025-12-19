SELECT player_id,
    player_name,
    ROUND((weight*0.453592) / (height_wo_shoes*0.0254 * height_wo_shoes*0.0254), 2) AS BMI
FROM anthro;