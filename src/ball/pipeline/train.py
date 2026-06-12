"""Train the per-forward-day injury models on the temporal split.

One model per forward day d in 1..Y. Two reference families plus one optional
comparison family:
  - Logistic Regression (interpretable baseline; class-balanced)
  - Gradient Boosting   (the V2 winner)
  - XGBoost             (optional comparison via --model all; needs the
                         requirements-xgb.txt dependency — never affects the
                         logreg/gboost reference numbers)

The split is temporal — earliest 80% of observation dates train, latest 20%
test. NEVER replace this with a random shuffle: that leaks future information
into training and invalidates every number (tests/test_temporal_split.py
guards this).

Artifacts written to $BALL_ARTIFACTS_DIR:
    preprocess.joblib      imputer + scaler (fit on the train window only)
    models_logreg.joblib   {forward_day: fitted LogisticRegression}
    models_gboost.joblib   {forward_day: fitted GradientBoostingClassifier}
    models_xgboost.joblib  {forward_day: fitted XGBClassifier}  (only with --model all)
    meta.json              feature columns, split, params, versions

Usage:
    python -m ball.pipeline.train [--horizon 14]
                                  [--model both|all|logreg|gboost|xgboost]
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

# Model families. `logreg` and `gboost` are the V2 reference families whose
# per-forward-day ROC-AUCs are frozen in reference/v2_results_2015-16.csv — do
# NOT alter how they are constructed. `xgboost` is an additive comparison family
# (optional dependency, see requirements-xgb.txt); it never touches the
# reference path. The CLI exposes named groups in FAMILY_GROUPS below.
REFERENCE_FAMILIES = ["logreg", "gboost"]
FAMILY_GROUPS = {
    "both": ["logreg", "gboost"],          # default: the reproducible reference pair
    "all": ["logreg", "gboost", "xgboost"],  # reference pair + XGBoost comparison
    "logreg": ["logreg"],
    "gboost": ["gboost"],
    "xgboost": ["xgboost"],
}

# Tuned XGBoost hyperparameters, chosen by ball.pipeline.tune_xgb on a temporal
# validation slice of the training window (the test hold-out is never used for
# tuning). scale_pos_weight is set per forward day at fit time, not here. Re-run
# `python -m ball.pipeline.tune_xgb` and paste its winner here to retune.
XGB_PARAMS = {
    "n_estimators": 800,
    "max_depth": 8,
    "learning_rate": 0.05,
    "subsample": 1.0,
    "colsample_bytree": 0.7,
    "min_child_weight": 3,
    "reg_lambda": 10.0,
    "gamma": 2.0,
}


def make_estimator(family: str, y_train: np.ndarray):
    """Return a fresh, unfitted estimator for one forward-day model.

    logreg/gboost reproduce the V2 reference exactly; xgboost is the optional
    comparison family (class-imbalance handled via per-day scale_pos_weight,
    mirroring logreg's class_weight='balanced')."""
    if family == "logreg":
        return LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=config.RANDOM_STATE
        )
    if family == "gboost":
        return GradientBoostingClassifier(random_state=config.RANDOM_STATE)
    if family == "xgboost":
        try:
            from xgboost import XGBClassifier
        except ModuleNotFoundError as exc:  # optional dependency
            raise SystemExit(
                "XGBoost is not installed. Install the optional comparison "
                "dependency with `make install-xgb` (or "
                "`pip install -r requirements-xgb.txt`), then retry."
            ) from exc
        pos = int(y_train.sum())
        neg = int(len(y_train) - pos)
        return XGBClassifier(
            **XGB_PARAMS,
            scale_pos_weight=(neg / pos) if pos else 1.0,
            eval_metric="logloss",
            tree_method="hist",
            n_jobs=1,  # single-threaded for reproducible AUCs
            random_state=config.RANDOM_STATE,
        )
    raise ValueError(f"unknown model family {family!r}")


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
        for fam in model_families:
            est = make_estimator(fam, ytr)
            est.fit(Xtr, ytr)
            models[fam][d] = est
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
    if "xgboost" in model_families:
        import xgboost
        meta["xgboost_version"] = xgboost.__version__
    return (imputer, scaler), models, meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizon", type=int, default=config.DEFAULT_FORWARD_DAYS)
    ap.add_argument("--model", choices=list(FAMILY_GROUPS), default="both",
                    help="which model family/families to train (default: both = "
                         "logreg+gboost reference pair; 'all' adds XGBoost)")
    ap.add_argument("--dataset", type=Path, default=None)
    args = ap.parse_args()

    dataset_file = args.dataset or config.dataset_path()
    if not dataset_file.exists():
        raise SystemExit(
            f"No dataset at {dataset_file} — run `python -m ball.pipeline.features` first."
        )
    dataset = load_dataset(dataset_file, args.horizon)
    families = FAMILY_GROUPS[args.model]
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
