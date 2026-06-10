"""X-day lookback feature aggregation (mean/std/min/max) + dataset assembly.

For every player-game observation, all games in the trailing `lookback` window
(inclusive of the observation date) are aggregated per raw feature into
mean/std/min/max. Together with the Y per-day targets this yields the design
matrix the per-forward-day models train on.

The loop is ported verbatim from evaluate_v2.build_v2 — do not "improve" the
math here without re-verifying against the reference results.

Usage:
    python -m ball.pipeline.features [--lookback 14] [--horizon 14]
                                     [--db PATH] [--output PATH]
"""
import argparse
from pathlib import Path

import pandas as pd

from ball.pipeline import config, data, targets

AGG_STATS = ["mean", "std", "min", "max"]


def feature_columns(df_columns) -> list:
    """Stat-major aggregate column order: <feature>_mean … then _std, _min, _max."""
    cols = []
    for stat in AGG_STATS:
        for c in data.RAW_FEATURES:
            if c in df_columns:
                cols.append(f"{c}_{stat}")
    return cols


def aggregate_window(window: pd.DataFrame, present: list) -> dict:
    """Aggregate one lookback window into {feature_stat: value}, NaN -> 0.0
    (a single-game window has no std)."""
    agg = window[present].agg(AGG_STATS)  # rows=stats, cols=features
    feat = {}
    for stat in AGG_STATS:
        for c in present:
            v = agg.loc[stat, c]
            feat[f"{c}_{stat}"] = 0.0 if pd.isna(v) else float(v)
    return feat


def build_dataset(df: pd.DataFrame, lookback_days: int, forward_days: int) -> pd.DataFrame:
    """One row per usable player-game: player_id, game_date, aggregate features,
    and injured_within_1..Y targets."""
    feat_cols = feature_columns(df.columns)
    present = [c for c in data.RAW_FEATURES if c in df.columns]

    rows, target_rows, dates, pids = [], [], [], []
    for pid, grp in df.groupby("player_id"):
        grp = grp.sort_values("game_date").reset_index(drop=True)
        injury_dates = grp.loc[grp["is_injured"] == 1, "game_date"].tolist()
        for i in range(len(grp)):
            row_date = grp.iloc[i]["game_date"]
            start = row_date - pd.Timedelta(days=lookback_days)
            mask = (grp["game_date"] <= row_date) & (grp["game_date"] >= start)
            window = grp.loc[mask]
            if window.empty:
                continue
            rows.append(aggregate_window(window, present))
            target_rows.append(targets.build_target_row(row_date, injury_dates, forward_days))
            dates.append(row_date)
            pids.append(pid)

    Xdf = pd.DataFrame(rows).reindex(columns=feat_cols).fillna(0.0)
    Tdf = pd.DataFrame(target_rows)
    Tdf.columns = [f"injured_within_{d}" for d in Tdf.columns]
    out = pd.concat(
        [pd.DataFrame({"player_id": pids, "game_date": dates}), Xdf, Tdf], axis=1
    )
    return out


def split_dataset(dataset: pd.DataFrame, forward_days: int):
    """Dataset frame -> (Xdf, Tdf with int day columns, dates series, feat_cols)."""
    target_cols = [f"injured_within_{d}" for d in range(1, forward_days + 1)]
    feat_cols = [c for c in dataset.columns if c not in {"player_id", "game_date", *target_cols}]
    Tdf = dataset[target_cols].copy()
    Tdf.columns = list(range(1, forward_days + 1))
    return dataset[feat_cols], Tdf, dataset["game_date"], feat_cols


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lookback", type=int, default=config.DEFAULT_LOOKBACK_DAYS)
    ap.add_argument("--horizon", type=int, default=config.DEFAULT_FORWARD_DAYS)
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    with data.connect(args.db) as conn:
        df = data.load_base(conn)
    print(
        f"Loaded {len(df)} player-game rows, {df['player_id'].nunique()} players, "
        f"{df['game_date'].min().date()} -> {df['game_date'].max().date()}"
    )
    dataset = build_dataset(df, args.lookback, args.horizon)
    n_feats = len(feature_columns(df.columns))
    print(f"Built dataset: {len(dataset)} observations x {n_feats} features, "
          f"lookback={args.lookback}d horizon={args.horizon}d")

    out = args.output or config.dataset_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(out, index=False)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
