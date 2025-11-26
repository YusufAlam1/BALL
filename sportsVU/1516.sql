-- Looking at games between October 27, 2015 and January 23, 2016
-- As these are games where we have GPS data available
-- With this we can find a player's injury, cross reference with the GPS data and extract insights from there

WITH injuries AS (
    SELECT *, COUNT(injury_id) OVER (PARTITION BY "Date") AS injury_count
    FROM injury_list
    WHERE (diagnosis IS NOT NULL OR 
        body_region IS NOT NULL) AND 
        "Date" BETWEEN '2015-10-01' AND '2016-01-23'
)
SELECT injury_id, 
    "Date", 
    team, 
    player_name, 
    player_id, 
    diagnosis, 
    body_region, 
    injury_count
FROM injuries
WHERE injury_count BETWEEN 1 AND 14
ORDER BY injury_count DESC, "Date" ASC;

-- Injury Candidate
-- Kevin Durant

-- Injury Dates: 2015-11-13, 2016-01-04
-- Important Games:
-- 2015-11-13 <- OKC VS 76ers
-- 2016-01-04 <- Kings VS OKC

-- However KD was already injured for these games check game before them
-- 2015-11-10 <- OKC VS Wizards
-- 2016-01-02 <- OKC VS Hornets






-- Opening Day Games 2015-2016 Season
-- 10.28.2015.CLE.at.MEM
-- 10.28.2015.DEN.at.HOU
-- 10.28.2015.IND.at.TOR
-- 10.28.2015.LAC.at.SAC
-- 10.28.2015.MIN.at.LAL
-- 10.28.2015.NOP.at.POR
-- 10.28.2015.NYK.at.MIL
-- 10.28.2015.PHI.at.BOS
-- 10.28.2015.SAS.at.OKC
-- 10.28.2015.UTA.at.DET
-- 10.28.2015.WAS.at.ORL