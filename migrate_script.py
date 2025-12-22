from dotenv import load_dotenv
import os
import pandas as pd
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE-URL")
SUPABASE_KEY = os.getenv("SUPABASE-API-KEY")

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
