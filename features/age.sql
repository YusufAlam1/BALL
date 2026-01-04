SELECT player_id,
    full_name,
    (CURRENT_DATE - birthdate) AS age_in_days
FROM players    
WHERE is_active = 'True';