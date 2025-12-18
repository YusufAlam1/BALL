import sqlite3
import psycopg2
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()

sqlite_conn = sqlite3.connect("Ball.db")
sqlite_cursor = sqlite_conn.cursor()

pg_conn = psycopg2.connect(
    dbname="BALL",
    user="postgres",
    password=os.getenv("PGSQL-PASS"),
    host="localhost",
    port=5432
)
pg_cursor = pg_conn.cursor()


# players table data transfer
sqlite_cursor.execute("SELECT id, full_name, first_name, last_name, is_active FROM players")
rows = sqlite_cursor.fetchall()

insert_query = """
    INSERT INTO players (player_id, full_name, first_name, last_name, is_active)
    VALUES (%s, %s, %s, %s, %s)
"""

for row in rows:
    row = list(row) # default type for row is tuple which is immutable
    if isinstance(row[4], int):
        row[4] = bool(row[4]) # sqlite may store bools as 0/1
    pg_cursor.execute(insert_query, row)

# anthro table data insertion
df = pd.read_csv("nba_api/data/draft_combine_anthro.csv")

df = df[[
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

df.columns = [
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

# replace empty values with Python None which gets mapped to NULL in PGSQL
df = df.where(pd.notnull(df), None)

insert_query = """
INSERT INTO anthro (
    player_id,
    height_w_o_shoes,
    height_w_o_shoes_ft_in,
    height_w_shoes,
    height_w_shoes_ft_in,
    weight,
    wingspan,
    wingspan_ft_in,
    standing_reach,
    standing_reach_ft_in,
    body_fat_pct,
    hand_length,
    hand_width
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (player_id) DO NOTHING;
"""

for _, row in df.iterrows():
    # row is still Panda.series, conver to basic tuple
    pg_cursor.execute(insert_query, tuple(row))