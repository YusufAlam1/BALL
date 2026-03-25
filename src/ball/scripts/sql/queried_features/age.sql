SELECT player_id,
    full_name,
    (CURRENT_DATE - birthdate) AS age_in_days
FROM players    
WHERE is_active = 'True';


-- ==================== POSTGRES / SUPABASE VERSION ====================
-- NOTE: birth_date is not currently in the Postgres schema.
-- If added to the anthro or players table, uncomment the age calculation.
SELECT p.player_id,
    p.full_name
    -- , (CURRENT_DATE - a.birth_date) AS age_in_days
FROM players p
-- JOIN anthro a ON a.player_id = p.player_id
WHERE p.is_active = TRUE;