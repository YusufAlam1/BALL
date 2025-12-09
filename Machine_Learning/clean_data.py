import sqlite3
import pandas as pd
import os

def get_cleaned_data(db_path):
    """
    connect to BALL.db, joins relevant tables, and cleans the data
    returns a pandas DF
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at: {db_path}")

    conn = sqlite3.connect(db_path)
    
    # query: join player game stats with player infor and team info
    query = """
    SELECT 
        pgs.*,
        p.full_name,
        p.height_w_shoes,
        p.weight,
        p.wingspan,
        t.nickname as team_name
    FROM PLAYER_GAME_STATS pgs
    LEFT JOIN PLAYER p ON pgs.player_id = p.player_id
    LEFT JOIN TEAM t ON pgs.team_id = t.team_id
    """
    
    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    # cleaning

    # 1. Convert 'min' (e.g., "34:12") to float minutes
    def time_to_float(t_str):
        if not isinstance(t_str, str): return 0.0
        try:
            if ':' in t_str:
                parts = t_str.split(':')
                return float(parts[0]) + float(parts[1])/60.0
            return float(t_str)
        except:
            return 0.0

    if 'min' in df.columns:
        df['minutes_float'] = df['min'].apply(time_to_float)
        # drop original min string
        df = df.drop(columns=['min'])

    # handle missing values
    # fill numeric NaNs with 0
    numeric_cols = df.select_dtypes(include=['number']).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    
    # fill categorical NaNs with "Unknown"
    categorical_cols = df.select_dtypes(include=['object']).columns
    df[categorical_cols] = df[categorical_cols].fillna("Unknown")

    # 3. drop duplicates
    df = df.drop_duplicates()

    return df
