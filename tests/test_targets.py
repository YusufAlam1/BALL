"""Target semantics: injury strictly after the observation date, within d days
(inclusive). One target column per forward day — the multi-target structure."""
import pandas as pd

from ball.pipeline import targets


def ts(s):
    return pd.Timestamp(s)


def test_injury_on_observation_date_does_not_count():
    tgt = targets.build_target_row(ts("2016-01-10"), [ts("2016-01-10")], 5)
    assert all(v == 0 for v in tgt.values())


def test_injury_within_window_counts_from_that_day_onward():
    tgt = targets.build_target_row(ts("2016-01-10"), [ts("2016-01-13")], 5)
    assert tgt == {1: 0, 2: 0, 3: 1, 4: 1, 5: 1}


def test_boundary_day_inclusive():
    tgt = targets.build_target_row(ts("2016-01-10"), [ts("2016-01-15")], 5)
    assert tgt[4] == 0 and tgt[5] == 1


def test_no_injuries():
    tgt = targets.build_target_row(ts("2016-01-10"), [], 3)
    assert tgt == {1: 0, 2: 0, 3: 0}


def test_injury_dates_by_player():
    df = pd.DataFrame(
        {
            "player_id": [1, 1, 2],
            "game_date": pd.to_datetime(["2016-01-01", "2016-01-05", "2016-01-02"]),
            "is_injured": [0, 1, 1],
        }
    )
    out = targets.injury_dates_by_player(df)
    assert out[1] == [ts("2016-01-05")] and out[2] == [ts("2016-01-02")]
