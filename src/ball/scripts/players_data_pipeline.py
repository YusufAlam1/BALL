from nba_api.stats.endpoints import commonallplayers
import sys
from pathlib import Path

# again, heavily consider moving connect.py to root
sys.path.append(str(Path(__file__).resolve().parent.parent / "db"))
from connect import supabase

def run():
    # 1. fetch from NBA API
    df = commonallplayers.CommonAllPlayers(
        is_only_current_season=0
    ).get_data_frames()[0]

    # 2. rename columns to match your schema
    df = df.rename(columns={
        "PERSON_ID": "player_id",
        "DISPLAY_FIRST_LAST": "full_name",
    })

    # 3. only keep columns your table actually has
    df = df[["player_id", "full_name"]]

    # 4. convert to list of dicts (what supabase expects)
    rows = df.to_dict(orient="records")

    # 5. upsert into supabase
    supabase.table("players").upsert(rows).execute()
    print(f"Upserted {len(rows)} players")

if __name__ == "__main__":
    run()