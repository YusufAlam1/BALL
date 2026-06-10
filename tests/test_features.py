"""Window aggregation: mean/std/min/max per raw feature over the X-day lookback,
NaN std (single-game windows) -> 0.0."""
import numpy as np
import pandas as pd

from ball.pipeline import features


def make_df():
    return pd.DataFrame(
        {
            "player_id": [1] * 3,
            "game_id": [10, 11, 12],
            "game_date": pd.to_datetime(["2016-01-01", "2016-01-05", "2016-01-30"]),
            "speed": [4.0, 6.0, 8.0],
            "minutes": [30.0, 20.0, 10.0],
            "is_injured": [0, 0, 1],
        }
    )


def test_aggregate_window_values():
    df = make_df()
    feat = features.aggregate_window(df.iloc[:2], ["speed", "minutes"])
    assert feat["speed_mean"] == 5.0
    assert feat["speed_std"] == np.std([4.0, 6.0], ddof=1)
    assert feat["speed_min"] == 4.0 and feat["speed_max"] == 6.0
    assert feat["minutes_mean"] == 25.0


def test_single_game_window_std_is_zero():
    df = make_df()
    feat = features.aggregate_window(df.iloc[:1], ["speed"])
    assert feat["speed_std"] == 0.0


def test_build_dataset_lookback_and_targets():
    df = make_df()
    out = features.build_dataset(df, lookback_days=14, forward_days=3)
    assert len(out) == 3  # every game has a non-empty window (includes itself)
    # second observation (2016-01-05): window holds games 1+2
    row = out.iloc[1]
    assert row["speed_mean"] == 5.0 and row["speed_max"] == 6.0
    # third observation (2016-01-30): first two games fall outside the 14d window
    row = out.iloc[2]
    assert row["speed_mean"] == 8.0 and row["speed_std"] == 0.0
    # injury happens ON 2016-01-30 -> strictly-after rule: its own targets are 0
    assert row["injured_within_3"] == 0
    # stat-major column order, only present raw features
    assert list(out.columns[:2]) == ["player_id", "game_date"]


def test_split_dataset_roundtrip():
    df = make_df()
    out = features.build_dataset(df, 14, 3)
    Xdf, Tdf, dates, feat_cols = features.split_dataset(out, 3)
    assert list(Tdf.columns) == [1, 2, 3]
    assert len(Xdf) == len(dates) == 3
    assert all(c.endswith(("_mean", "_std", "_min", "_max")) for c in feat_cols)
