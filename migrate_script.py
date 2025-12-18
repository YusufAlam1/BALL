import psycopg2
from dotenv import load_dotenv
import os
import pandas as pd
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# players table data transfer
df_players = pd.read_csv("nba_api/data/players.csv")
df_players = df_players.where(pd.notnull(df_players), None)

# potentially redundant type conversion for safety
df_players['is_active'] = df_players['is_active'].astype(bool)

for _, row in df_players.iterrows():
    supabase.table("players").insert({
        "player_id": row["id"],
        "full_name": row["full_name"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "is_active": row["is_active"]
    }).execute()


# anthro table data insertion
df_anthro = pd.read_csv("nba_api/data/draft_combine_anthro.csv")

df_anthro = df_anthro[[
    "PLAYER_ID",
    "HEIGHT_WO_SHOES",
    "HEIGHT_WO_SHOES_FT_IN",
    "HEIGHT_W_SHOES",
    "HEIGHT_W_SHOES_FT_IN",
    "WEIGHT",
    "WINGSPAN",
    "WINGSPAN_FT_IN",
    "STANDING_REACH",
    "STANDING_REACH_FT_IN",
    "BODY_FAT_PCT",
    "HAND_LENGTH",
    "HAND_WIDTH"
]]

# rename to match DB
df_anthro.columns = [
    "player_id",
    "height_w_o_shoes",
    "height_w_o_shoes_ft_in",
    "height_w_shoes",
    "height_w_shoes_ft_in",
    "weight",
    "wingspan",
    "wingspan_ft_in",
    "standing_reach",
    "standing_reach_ft_in",
    "body_fat_pct",
    "hand_length",
    "hand_width"
]

df_anthro = df_anthro.where(pd.notnull(df_anthro), None)

for _, row in df_anthro.iterrows():
    supabase.table("anthro").insert(row.to_dict()).execute()
