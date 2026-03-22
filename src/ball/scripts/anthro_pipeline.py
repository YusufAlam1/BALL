from nba_api.stats.endpoints import draftcombineplayeranthro
import sys
from pathlib import Path
import time
sys.path.append(str(Path(__file__).resolve().parent.parent / "db"))
from connect import supabase

'''
LATEST SEASON ONLY VERSION
'''
def run_latest_season():
    # fetch from NBA API
    df = draftcombineplayeranthro.DraftCombinePlayerAnthro().get_data_frames()[0]

    # rename columns to match schema
    df = df.rename(columns={
        "PLAYER_ID": "player_id",
        "HEIGHT_WO_SHOES": "height_wo_shoes",
        "HEIGHT_WO_SHOES_FT_IN": "height_wo_shoes_ft_in",
        "HEIGHT_W_SHOES": "height_w_shoes",
        "HEIGHT_W_SHOES_FT_IN": "height_w_shoes_ft_in",
        "WEIGHT": "weight",
        "WINGSPAN": "wingspan",
        "WINGSPAN_FT_IN": "wingspan_ft_in",
        "STANDING_REACH": "standing_reach",
        "STANDING_REACH_FT_IN": "standing_reach_ft_in",
        "BODY_FAT_PCT": "body_fat_pct",
        "HAND_LENGTH": "hand_length",
        "HAND_WIDTH": "hand_width",
    })

    # only keep columns schema actually has
    df = df[["player_id", "height_wo_shoes", "height_wo_shoes_ft_in",
                      "height_w_shoes", "height_w_shoes_ft_in", "weight",
                      "wingspan", "wingspan_ft_in", "standing_reach",
                      "standing_reach_ft_in", "body_fat_pct", "hand_length",
                      "hand_width"]]

    # convert to list of dicts for insertion
    rows = df.to_dict(orient="records")

    # upsert into supabase
    supabase.table("players").upsert(rows).execute()
    print(f"Upserted {len(rows)} rows into anthro")

'''
2000-2025 SEASONS VERSION
'''
SEASONS = [str(year) for year in range(2000, 2025)]

def run_many_seasons():
    all_rows = []

    for season in SEASONS:
        print(f"Fetching season {season}...")
        try:
            df = draftcombineplayeranthro.DraftCombinePlayerAnthro(
                season_year=season
            ).get_data_frames()[0]

            if df.empty:
                print(f"  No data for {season}, skipping")
                continue

            df = df.rename(columns={
                "PLAYER_ID": "player_id",
                "HEIGHT_WO_SHOES": "height_wo_shoes",
                "HEIGHT_WO_SHOES_FT_IN": "height_wo_shoes_ft_in",
                "HEIGHT_W_SHOES": "height_w_shoes",
                "HEIGHT_W_SHOES_FT_IN": "height_w_shoes_ft_in",
                "WEIGHT": "weight",
                "WINGSPAN": "wingspan",
                "WINGSPAN_FT_IN": "wingspan_ft_in",
                "STANDING_REACH": "standing_reach",
                "STANDING_REACH_FT_IN": "standing_reach_ft_in",
                "BODY_FAT_PCT": "body_fat_pct",
                "HAND_LENGTH": "hand_length",
                "HAND_WIDTH": "hand_width",
            })

            df = df[["player_id", "height_wo_shoes", "height_wo_shoes_ft_in",
                      "height_w_shoes", "height_w_shoes_ft_in", "weight",
                      "wingspan", "wingspan_ft_in", "standing_reach",
                      "standing_reach_ft_in", "body_fat_pct", "hand_length",
                      "hand_width"]]

            all_rows.extend(df.to_dict(orient="records"))
            print(f"  Got {len(df)} players")

        except Exception as e:
            print(f"  Error for {season}: {e}")

        time.sleep(0.5)  # rate limiting

    if all_rows:
        supabase.table("anthro").upsert(all_rows).execute()
        print(f"Upserted {len(all_rows)} rows")

if __name__ == "__main__":
    run_latest_season()