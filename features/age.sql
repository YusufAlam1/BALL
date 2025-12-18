SELECT id,
    full_name,
    CAST(Julianday('now') - Julianday(birthdate) AS INTEGER) AS age_in_days
FROM players