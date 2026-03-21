# pipeline_sportsvu.py
import json
import os
from pathlib import Path
import sys

# I love python and needing to add to the search list - maybe we could add connect.py to the root for ease of access
sys.path.append(str(Path(__file__).resolve().parent.parent / "db")) 

from connect import supabase

def process_game(file_path: str):
    with open(file_path, "r") as f:
        data = json.load(f)

    game_id = Path(file_path).stem   # filename without .json
    rows = []

    # json parse into row array for insertion
    for event in data["events"]:
        event_id = event["eventId"]
        for moment in event["moments"]:
            quarter, game_clock, shot_clock = moment[0], moment[2], moment[3]
            for player in moment[5]:
                team_id, player_id, x, y, z = player
                rows.append({
                    "game_id": int(game_id),
                    "event_id": int(event_id),
                    "player_id": int(player_id),
                    "team_id": int(team_id),
                    "x_loc": x,
                    "y_loc": y,
                    "radius": z,
                    "game_clock": str(game_clock),
                    "shot_clock": str(shot_clock),
                    "quarter": quarter,
                })

    # Insert in batches of 500 (Supabase has row limits per request)
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        supabase.table("sportsvu").upsert(batch).execute() # upsert for if row already exists
        print(f"  Inserted rows {i} to {i+len(batch)}")

    print(f"Done: {game_id} — {len(rows):,} rows")


def run(data_dir: str):
    json_files = list(Path(data_dir).rglob("*.json")) # recursive search inside folder for json files
    print(f"Found {len(json_files)} JSON files")
    for f in json_files:
        process_game(str(f))


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent / "data" # must be edited if repo structure changes
    run(data_dir)