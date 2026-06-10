"""Train the per-forward-day injury models on the temporal split.

One model per forward day d in 1..Y, two families:
  - Logistic Regression (interpretable baseline; class-balanced)
  - Gradient Boosting   (the V2 winner)

The split is temporal — earliest 80% of observation dates train, latest 20%
test. NEVER replace this with a random shuffle: that leaks future information
into training and invalidates every number (tests/test_temporal_split.py
guards this).

Artifacts written to $BALL_ARTIFACTS_DIR:
    preprocess.joblib      imputer + scaler (fit on the train window only)
    models_logreg.joblib   {forward_day: fitted LogisticRegression}
    models_gboost.joblib   {forward_day: fitted GradientBoostingClassifier}
    meta.json              feature columns, split, params, versions

Usage:
    python -m ball.pipeline.train [--horizon 14] [--model both|logreg|gboost]
                                  [--dataset PATH]
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from ball.pipeline import config, features

# Skip a forward day when positives are too sparse to train/score meaningfully —
# same rule as the reference implementation.
MIN_TRAIN_POSITIVES = 5
MIN_TEST_POSITIVES = 1


def temporal_split(date_values: np.ndarray, train_fraction: float = config.TRAIN_FRACTION):
    """Indices (train, test): earliest `train_fraction` of dates train, rest test."""
    order = np.argsort(date_values)
    cut = int(len(order) * train_fraction)
    return order[:cut], order[cut:]


def load_dataset(path: Path, horizon: int):
    # round_trip: the default fast float parser is ~1 ulp lossy, which is enough
    # to nudge LogisticRegression's optimizer and shift AUCs in the 3rd decimal.
    dataset = pd.read_csv(path, parse_dates=["game_date"], float_precision="round_trip")
    missing = [c for c in (f"injured_within_{d}" for d in range(1, horizon + 1))
               if c not in dataset.columns]
    if missing:
        raise SystemExit(
            f"Dataset {path} lacks target columns {missing[:3]}… — rebuild with "
            f"`python -m ball.pipeline.features --horizon {horizon}`."
        )
    return dataset


def train(dataset: pd.DataFrame, horizon: int, model_families: list):
    Xdf, Tdf, dates, feat_cols = features.split_dataset(dataset, horizon)
    tr, te = temporal_split(dates.values)

    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    Xtr = scaler.fit_transform(imputer.fit_transform(Xdf.values[tr]))

    models = {fam: {} for fam in model_families}
    skipped = []
    for d in range(1, horizon + 1):
        y = Tdf[d].values
        ytr, yte = y[tr], y[te]
        if ytr.sum() < MIN_TRAIN_POSITIVES or yte.sum() < MIN_TEST_POSITIVES:
            skipped.append(d)
            print(f"  day {d:>2}: skipped ({int(ytr.sum())} train / {int(yte.sum())} test positives)")
            continue
        if "logreg" in model_families:
            lr = LogisticRegression(
                max_iter=2000, class_weight="balanced", random_state=config.RANDOM_STATE
            )
            lr.fit(Xtr, ytr)
            models["logreg"][d] = lr
        if "gboost" in model_families:
            gb = GradientBoostingClassifier(random_state=config.RANDOM_STATE)
            gb.fit(Xtr, ytr)
            models["gboost"][d] = gb
        print(f"  day {d:>2}: trained {'+'.join(model_families)} "
              f"({int(ytr.sum())} train positives)")

    meta = {
        "feature_cols": feat_cols,
        "horizon": horizon,
        "train_fraction": config.TRAIN_FRACTION,
        "cut": int(len(dates) * config.TRAIN_FRACTION),
        "n_observations": int(len(dates)),
        "skipped_days": skipped,
        "model_families": model_families,
        "random_state": config.RANDOM_STATE,
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    return (imputer, scaler), models, meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizon", type=int, default=config.DEFAULT_FORWARD_DAYS)
    ap.add_argument("--model", choices=["both", "logreg", "gboost"], default="both")
    ap.add_argument("--dataset", type=Path, default=None)
    args = ap.parse_args()

    dataset_file = args.dataset or config.dataset_path()
    if not dataset_file.exists():
        raise SystemExit(
            f"No dataset at {dataset_file} — run `python -m ball.pipeline.features` first."
        )
    dataset = load_dataset(dataset_file, args.horizon)
    families = ["logreg", "gboost"] if args.model == "both" else [args.model]
    print(f"Training {families} on {len(dataset)} observations, horizon {args.horizon}d "
          f"(temporal {round(config.TRAIN_FRACTION * 100)}/{round((1 - config.TRAIN_FRACTION) * 100)} split)")

    (imputer, scaler), models, meta = train(dataset, args.horizon, families)

    art = config.artifacts_dir()
    joblib.dump({"imputer": imputer, "scaler": scaler}, art / "preprocess.joblib")
    for fam in families:
        joblib.dump(models[fam], art / f"models_{fam}.joblib")
    (art / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Saved artifacts to {art}: preprocess.joblib, "
          + ", ".join(f"models_{f}.joblib" for f in families) + ", meta.json")


if __name__ == "__main__":
    main()
