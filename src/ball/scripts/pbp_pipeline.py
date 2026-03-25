from nba_api.stats.endpoints import playbyplayv3, leaguegamefinder
import sys
from pathlib import Path
import time
import re

sys.path.append(str(Path(__file__).resolve().parent.parent / "db"))
from connect import supabase

SEASONS = ["2015-16", "2016-17", "2017-18", "2018-19", "2019-20",
           "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]

def parse_clock(clock_str: str) -> str | None:
    """Convert PT12M00.00S to HH:MM:SS for TIME column."""
    if not clock_str:
        return None
    m = re.match(r"PT(\d+)M([\d.]+)S", clock_str)
    if not m:
        return None
    minutes = int(m.group(1))
    seconds = int(float(m.group(2)))
    return f"00:{minutes:02d}:{seconds:02d}"

def get_game_ids(season: str) -> list:
    df = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        league_id_nullable="00",
        season_type_nullable="Regular Season"
    ).get_data_frames()[0]
    # returns (game_id, game_date) so we can fill game_date too
    return df[["GAME_ID", "GAME_DATE"]].drop_duplicates("GAME_ID").values.tolist()

def process_game(game_id: str, game_date: str):
    df = playbyplayv3.PlayByPlayV3(
        game_id=game_id
    ).get_data_frames()[1]  # index 1 is PlayByPlay, index 0 is AvailableVideo

    if df.empty:
        return 0

    df["event_time"] = df["clock"].apply(parse_clock)
    df["game_date"] = game_date

    # replace 0 with None for foreign keys since 0 is not a valid player/team id
    df["personId"] = df["personId"].replace(0, None)
    df["teamId"] = df["teamId"].replace(0, None)

    df = df.rename(columns={
        "gameId": "game_id",
        "actionNumber": "event_id",
        "teamId": "team_id",
        "personId": "player_id",
        "actionType": "event_type",
        "scoreHome": "home_score",
        "scoreAway": "away_score",
    })

    df = df[["game_id", "event_id", "player_id", "team_id",
             "game_date", "event_time", "event_type", "description",
             "home_score", "away_score"]]

    rows = df.to_dict(orient="records")
    supabase.table("pbp").upsert(rows).execute()
    return len(rows)

def run():
    for season in SEASONS:
        print(f"\nFetching game IDs for {season}...")
        try:
            games = get_game_ids(season)
            print(f"  Found {len(games)} games")
        except Exception as e:
            print(f"  Failed to get game IDs for {season}: {e}")
            continue

        for i, (game_id, game_date) in enumerate(games):
            try:
                n = process_game(game_id, game_date)
                print(f"  [{i+1}/{len(games)}] game {game_id} -> {n} rows")
            except Exception as e:
                print(f"  [{i+1}/{len(games)}] game {game_id} failed: {e}")

            time.sleep(0.6)

if __name__ == "__main__":
    run()