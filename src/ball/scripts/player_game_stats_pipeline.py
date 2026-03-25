from nba_api.stats.endpoints import boxscoretraditionalv3, leaguegamefinder
import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).resolve().parent.parent / "db"))
from connect import supabase

'''
================================================
NOTE: Adequate rate limiting is not complete yet
================================================
'''

SEASONS = ["2015-16", "2016-17", "2017-18", "2018-19", "2019-20", 
           "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]

def get_game_ids(season: str) -> list:
    df = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        league_id_nullable="00",
        season_type_nullable="Regular Season"
    ).get_data_frames()[0]
    return df["GAME_ID"].unique().tolist()

def process_game(game_id: str):
    df = boxscoretraditionalv3.BoxScoreTraditionalV3(
        game_id=game_id
    ).get_data_frames()[0]  # index 0 is PlayerStats

    if df.empty:
        return 0

    # combine first and last name
    df["player_name"] = df["firstName"] + " " + df["familyName"]

    df = df.rename(columns={
        "gameId": "game_id",
        "teamId": "team_id",
        "teamCity": "team_city",
        "teamTricode": "team_abbreviation",
        "personId": "player_id",
        "position": "start_position",
        "minutes": "min",
        "fieldGoalsMade": "fgm",
        "fieldGoalsAttempted": "fga",
        "fieldGoalsPercentage": "fg_pct",
        "threePointersMade": "fg3m",
        "threePointersAttempted": "fg3a",
        "threePointersPercentage": "fg3_pct",
        "freeThrowsMade": "ftm",
        "freeThrowsAttempted": "fta",
        "freeThrowsPercentage": "ft_pct",
        "reboundsOffensive": "oreb",
        "reboundsDefensive": "dreb",
        "reboundsTotal": "reb",
        "assists": "ast",
        "steals": "stl",
        "blocks": "blk",
        "foulsPersonal": "pf",
        "points": "pts",
        "plusMinusPoints": "plus_minus",
    })

    df = df[["game_id", "team_id", "team_city", "team_abbreviation",
             "player_id", "player_name", "start_position", "comment",
             "min", "fgm", "fga", "fg_pct", "fg3m", "fg3a", "fg3_pct",
             "ftm", "fta", "ft_pct", "oreb", "dreb", "reb", "ast",
             "stl", "blk", "turnovers", "pf", "pts", "plus_minus"]]

    rows = df.to_dict(orient="records")
    supabase.table("player_game_stats").upsert(rows).execute()
    return len(rows)

def run():
    for season in SEASONS:
        print(f"\nFetching game IDs for {season}...")
        try:
            game_ids = get_game_ids(season)
            print(f"  Found {len(game_ids)} games")
        except Exception as e:
            print(f"  Failed to get game IDs for {season}: {e}")
            continue

        for i, game_id in enumerate(game_ids):
            try:
                n = process_game(game_id)
                print(f"  [{i+1}/{len(game_ids)}] game {game_id} -> {n} rows")
            except Exception as e:
                print(f"  [{i+1}/{len(game_ids)}] game {game_id} failed: {e}")

            time.sleep(0.6)  # rate limiting, likely needs adjusting

if __name__ == "__main__":
    run()