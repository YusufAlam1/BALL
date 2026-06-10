"""The split must stay temporal: every training observation predates every test
observation. A random shuffle here leaks future data and invalidates all
reported numbers — this guard exists so that can never sneak back in."""
import inspect

import numpy as np
import pandas as pd

from ball.pipeline import train


def test_train_dates_all_precede_test_dates():
    rng = np.random.RandomState(0)
    dates = pd.to_datetime("2015-10-01") + pd.to_timedelta(rng.randint(0, 200, size=500), "D")
    tr, te = train.temporal_split(dates.values)
    assert len(tr) + len(te) == 500
    assert dates.values[tr].max() <= dates.values[te].min()


def test_split_fraction():
    dates = pd.date_range("2015-01-01", periods=100).values
    tr, te = train.temporal_split(dates, train_fraction=0.8)
    assert len(tr) == 80 and len(te) == 20


def test_no_random_shuffle_in_train_source():
    src = inspect.getsource(train)
    assert "train_test_split" not in src, "train.py must not use sklearn's random split"
    assert "shuffle(" not in src, "train.py must not shuffle observations"
    assert "permutation(" not in src, "train.py must not permute observation order"
