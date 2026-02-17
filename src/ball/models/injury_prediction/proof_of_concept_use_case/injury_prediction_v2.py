"""
Injury prediction v2: X-day lookback features, Y-day forward targets.
Utilities for loading data, building features, and predicting injury likelihood.
"""
import os
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from thefuzz import fuzz


# Resolve DB path relative to this file (v2 -> injury_prediction -> models -> ball)
V2_DIR = Path(__file__).resolve().parent
BALL_DIR = V2_DIR.parent.parent.parent  # src/ball
DB_PATH = BALL_DIR / "db" / "BALL.db"


def get_engine():
    """Return sqlite connection."""
    return sqlite3.connect(str(DB_PATH))


def load_base_data(conn=None):
    """Load base game-level data from SQL."""
    sql_path = V2_DIR / "model_input_base.sql"
    with open(sql_path) as f:
        sql = f.read()
    if conn is None:
        conn = get_engine()
    df = pd.read_sql(sql, conn)
    if conn is None:
        conn.close()
    return df


def load_injury_dates(conn=None):
    """Load injury dates (relinquished)."""
    sql_path = V2_DIR / "injury_dates.sql"
    with open(sql_path) as f:
        sql = f.read()
    if conn is None:
        conn = get_engine()
    df = pd.read_sql(sql, conn)
    if conn is None:
        conn.close()
    df["injury_date"] = pd.to_datetime(df["injury_date"])
    return df


def load_player_list(conn=None):
    """Load player list for fuzzy search."""
    sql_path = V2_DIR / "player_list.sql"
    with open(sql_path) as f:
        sql = f.read()
    if conn is None:
        conn = get_engine()
    df = pd.read_sql(sql, conn)
    if conn is None:
        conn.close()
    return df


def load_player_lookback(player_id: int, lookback_days: int, conn=None):
    """Load games for a player within the lookback window."""
    sql_path = V2_DIR / "player_lookback.sql"
    with open(sql_path) as f:
        sql = f.read()
    if conn is None:
        conn = get_engine()
    df = pd.read_sql(sql, conn, params=(player_id, player_id, str(lookback_days)))
    if conn is None:
        conn.close()
    return df


def parse_minutes(val):
    """Convert minutes from MM:SS to float."""
    if pd.isna(val) or val == "":
        return np.nan
    s = str(val).strip()
    parts = s.split(":")
    if len(parts) == 2:
        return float(parts[0]) + float(parts[1]) / 60.0
    try:
        return float(s)
    except ValueError:
        return np.nan


def build_features_targets(
    base_df: pd.DataFrame,
    injury_df: pd.DataFrame,
    lookback_days: int,
    forward_days: int,
):
    """
    Build training data: X-day lookback aggregates -> Y-day forward targets.
    Returns:
        features_df: one row per player-game, aggregated features from lookback window
        targets_df: columns injured_within_1, injured_within_2, ..., injured_within_Y
    """
    base_df = base_df.copy()
    base_df["game_date"] = pd.to_datetime(base_df["game_date"])
    base_df = base_df.sort_values(["player_id", "game_date"]).reset_index(drop=True)

    # Parse minutes and coerce numeric columns
    if "minutes" in base_df.columns:
        base_df["minutes"] = base_df["minutes"].apply(parse_minutes)
    for c in base_df.columns:
        if c not in {"player_id", "full_name", "game_date", "game_id"}:
            base_df[c] = pd.to_numeric(base_df[c], errors="coerce")

    # Injury dates per player
    injury_by_player = (
        injury_df.groupby("player_id")["injury_date"]
        .apply(lambda x: x.sort_values().tolist())
        .to_dict()
    )

    # Numeric feature columns (exclude ids, dates, names)
    exclude = {"player_id", "full_name", "game_date", "game_id"}
    numeric_cols = [
        c for c in base_df.columns
        if c not in exclude and base_df[c].dtype in [np.float64, np.int64, np.float32, np.int32, float, int]
    ]
    rows = []
    targets = []

    for (player_id,), grp in base_df.groupby(["player_id"]):
        grp = grp.sort_values("game_date").reset_index(drop=True)
        injury_dates = injury_by_player.get(player_id, [])

        for i in range(len(grp)):
            row_date = grp.iloc[i]["game_date"]
            # Lookback window: games in [row_date - lookback_days, row_date]
            lookback_start = row_date - pd.Timedelta(days=lookback_days)
            lookback_games = grp[(grp["game_date"] <= row_date) & (grp["game_date"] >= lookback_start)]
            if len(lookback_games) == 0:
                continue

            # Aggregate features (mean over lookback)
            agg = lookback_games[numeric_cols].agg(["mean", "std", "min", "max"]).stack()
            agg.index = [f"{c}_{s}" for c, s in agg.index]
            feat_row = agg.to_dict()
            # Fill NaN std with 0
            for k, v in feat_row.items():
                if pd.isna(v):
                    feat_row[k] = 0.0

            # Targets: injured within 1, 2, ..., forward_days
            target_row = {}
            for d in range(1, forward_days + 1):
                end_date = row_date + pd.Timedelta(days=d)
                injured = any(
                    idate > row_date and idate <= end_date
                    for idate in injury_dates
                )
                target_row[f"injured_within_{d}"] = 1 if injured else 0

            rows.append({**feat_row, "player_id": player_id, "game_date": row_date, "game_id": grp.iloc[i]["game_id"]})
            targets.append(target_row)

    features_df = pd.DataFrame(rows)
    targets_df = pd.DataFrame(targets)
    feat_cols = [c for c in features_df.columns if c not in {"player_id", "game_date", "game_id"}]
    return features_df, targets_df, feat_cols


def fuzzy_match_player(query: str, players_df: pd.DataFrame, threshold: int = 60):
    """
    Fuzzy match player name. Returns (player_id, full_name, score) or (None, None, 0).
    """
    from thefuzz import fuzz
    query = (query or "").strip()
    if not query:
        return None, None, 0
    best_id, best_name, best_score = None, None, 0
    for _, row in players_df.iterrows():
        name = str(row["full_name"]) if pd.notna(row["full_name"]) else ""
        s1 = fuzz.ratio(query.lower(), name.lower())
        s2 = fuzz.partial_ratio(query.lower(), name.lower())
        score = max(s1, s2)
        if score >= threshold and score > best_score:
            best_score = score
            best_id = row["player_id"]
            best_name = name
    return best_id, best_name, best_score


def _parse_feature_name(fc: str):
    """
    Parse feature name into (base_col, stat).
    Supports prefix format (mean_age, std_speed) and suffix format (age_mean, speed_std).
    Returns (base, stat) or None if not an agg feature.
    """
    fc = str(fc).strip().lower()
    for stat in ("mean", "std", "min", "max"):
        if fc.startswith(stat + "_"):
            return (fc[len(stat) + 1 :], stat)
        if fc.endswith("_" + stat):
            return (fc[: -len(stat) - 1], stat)
    return None


def aggregate_for_prediction(games_df: pd.DataFrame, feature_cols: list):
    """
    Aggregate player's lookback games into a single feature row for prediction.
    feature_cols: model's expected column names (e.g. mean_age, speed_std, ...).
    Supports both prefix (mean_age) and suffix (age_mean) naming.
    Returns dict with keys matching feature_cols, or None if games_df empty.
    """
    if games_df.empty:
        return None
    games_df = games_df.copy()
    games_df.columns = [str(c).strip().lower() for c in games_df.columns]
    if "minutes" in games_df.columns:
        games_df["minutes"] = games_df["minutes"].apply(parse_minutes)
    for c in games_df.columns:
        if c not in {"player_id", "full_name", "game_date", "game_id"}:
            games_df[c] = pd.to_numeric(games_df[c], errors="coerce")
    base_cols_set = set()
    for fc in feature_cols:
        parsed = _parse_feature_name(fc)
        if parsed:
            base_cols_set.add(parsed[0])
    cols_lower_to_actual = {c.lower(): c for c in games_df.columns}
    base_cols = [cols_lower_to_actual[b] for b in base_cols_set if b in cols_lower_to_actual]
    if not base_cols:
        return None
    agg = games_df[base_cols].agg(["mean", "std", "min", "max"]).stack()
    agg.index = [f"{c}_{s}" for c, s in agg.index]
    row_suffix = {k.lower(): (0.0 if pd.isna(v) else float(v)) for k, v in agg.to_dict().items()}
    out = {}
    for fc in feature_cols:
        fc_str = str(fc).strip()
        parsed = _parse_feature_name(fc_str)
        if parsed:
            base, stat = parsed
            key = f"{base}_{stat}"
            out[fc_str] = row_suffix.get(key, 0.0)
        else:
            out[fc_str] = 0.0
    return out
