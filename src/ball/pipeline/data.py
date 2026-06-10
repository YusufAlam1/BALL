"""SQLite data access for the pipeline and the Streamlit app.

`load_base` reproduces evaluate_v2.load_data() exactly (same merge, same
parsing, same sort) so the extracted pipeline yields identical numbers.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from ball.pipeline import config

# Raw game-level feature columns (lowercased) aggregated over the lookback window.
RAW_FEATURES = [
    "age", "speed", "distance", "height_wo_shoes", "weight", "wingspan",
    "standing_reach", "body_fat_pct", "hand_length", "hand_width",
    "minutes", "usagepercentage", "pace", "possessions",
]


def connect(db: Path | None = None) -> sqlite3.Connection:
    db = db or config.db_path()
    if not db.exists():
        raise FileNotFoundError(
            f"SQLite store not found at {db}. Run `python -m ball.pipeline.bootstrap` first "
            f"(or set BALL_DB_PATH)."
        )
    return sqlite3.connect(db)


def parse_minutes(val):
    """MM:SS -> float minutes."""
    if pd.isna(val) or val == "":
        return np.nan
    s = str(val).strip()
    if ":" in s:
        m, sec = s.split(":")[:2]
        try:
            return float(m) + float(sec) / 60.0
        except ValueError:
            return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def load_base(conn: sqlite3.Connection) -> pd.DataFrame:
    """Game-level rows with game_date, numeric features parsed, sorted by player/date."""
    # ORDER BY rowid pins insertion (= CSV) order so downstream sorts/splits are
    # bit-identical to the reference implementation that read the CSVs directly.
    df = pd.read_sql("SELECT * FROM model_input ORDER BY rowid", conn)
    df.columns = [c.lower() for c in df.columns]
    gd = pd.read_sql("SELECT * FROM game_dates ORDER BY rowid", conn)
    gd.columns = [c.lower() for c in gd.columns]
    gd["game_date"] = pd.to_datetime(gd["game_date"])
    df = df.merge(gd, on="game_id", how="left")
    df["minutes"] = df["minutes"].apply(parse_minutes)
    for c in RAW_FEATURES:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = (
        df.dropna(subset=["game_date"])
        .sort_values(["player_id", "game_date"])
        .reset_index(drop=True)
    )
    return df


def load_players(conn: sqlite3.Connection) -> pd.DataFrame:
    """Players that actually appear in the model input (for fuzzy name search)."""
    return pd.read_sql(
        """
        SELECT DISTINCT p.player_id, p.full_name
        FROM players p
        JOIN model_input m ON m.player_id = p.player_id
        ORDER BY p.full_name
        """,
        conn,
    )


def load_player_games(conn: sqlite3.Connection, player_id: int) -> pd.DataFrame:
    """All of one player's games with dates, parsed like load_base, oldest first."""
    df = pd.read_sql(
        "SELECT * FROM model_input WHERE player_id = ? ORDER BY rowid",
        conn,
        params=(int(player_id),),
    )
    if df.empty:
        return df
    gd = pd.read_sql("SELECT * FROM game_dates ORDER BY rowid", conn)
    gd["game_date"] = pd.to_datetime(gd["game_date"])
    df = df.merge(gd, on="game_id", how="left")
    df["minutes"] = df["minutes"].apply(parse_minutes)
    for c in RAW_FEATURES:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["game_date"]).sort_values("game_date").reset_index(drop=True)
