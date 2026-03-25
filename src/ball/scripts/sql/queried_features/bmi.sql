SELECT p.player_id,
    full_name
  -- ROUND(
  --   ((weight * 0.453592) /
  --    (height_wo_shoes * 0.0254 * height_wo_shoes * 0.0254))::numeric,
  --   2
  -- ) AS bmi
FROM anthro a
JOIN players p ON a.player_id = p.player_id;


-- ==================== POSTGRES / SUPABASE VERSION ====================
-- Column name fix: height_wo_shoes -> height_w_o_shoes (per postgre_schema.sql)

SELECT p.player_id,
    p.full_name,
    ROUND(
      ((a.weight * 0.453592) /
       (a.height_w_o_shoes * 0.0254 * a.height_w_o_shoes * 0.0254))::numeric,
      2
    ) AS bmi
FROM anthro a
JOIN players p ON a.player_id = p.player_id;