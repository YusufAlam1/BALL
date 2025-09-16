-- Base Query: What is the average likelihood_of_injury across all players?
SELECT AVG(likelihood_of_injury) AS avg_injury_chance
FROM injuries;
-- Result: avg_injury_chance = 0.500


-- Question: Does BMI have an impact on likelihood_of_injury?
-- * player_weight is in kg
-- * player_height is in cm
-- * AVG(BMI) = 23.3514175434984
WITH bmi_injury AS (
    SELECT *, player_weight / ((player_height/100) * (player_height/100)) AS BMI
    FROM injuries
)
SELECT AVG(likelihood_of_injury) AS avg_injury_chance_bmi
FROM bmi_injury
WHERE BMI > (SELECT AVG(BMI) FROM bmi_injury);
-- Result: avg_injury_chance_bmi = 0.500 (No impact)
 

-- Question: Does age have an impact on likelihood_of_injury?
WITH overall AS (
  SELECT AVG(likelihood_of_injury) AS p0 FROM injuries
),
subset AS (
  SELECT COUNT(*) AS n,
         AVG(likelihood_of_injury) AS p_hat
  FROM injuries
  WHERE player_age > (SELECT AVG(player_age) FROM injuries)
)
SELECT
  n,
  p_hat,
  p0,
  (p_hat - p0) / SQRT(p0 * (1 - p0) / n) AS z_score
FROM subset, overall;
-- Result: avg_injury_chance_age = 0.520 
-- Z-score = 0.90
-- P-value = 0.1841
-- (Not significant enough to say theres a difference)