"""Tune the XGBoost comparison family with a temporal validation split.

This NEVER tunes on the test set. The latest-20% temporal hold-out that
evaluate.py reports is left completely untouched here; hyperparameters are
scored on a temporal *validation* slice carved out of the training window only,
so no future information leaks into the search (tests/test_temporal_split.py
guards the train/test boundary, and the validation slice sits strictly before
the test hold-out in time).

Procedure (nested temporal CV, the direction CLAUDE.md asks for):
  1. Temporal train/test split — test reserved, never seen in this module.
  2. Within train: expanding-window temporal CV (k folds). Each fold trains on
     an earlier block and validates on the next; all folds sit strictly before
     the test hold-out, so there is no leakage. Averaging over folds — instead
     of a single slice — stops the search from rewarding configs that only look
     good on one noisy validation cut (a real risk on one season of sparse
     injuries: a single split picked an overfit max_depth=8 config that lost on
     the test set).
  3. Randomized search over the XGBoost space. Each candidate is fit per forward
     day per fold with early stopping, then scored by the mean validation
     ROC-AUC across folds and horizons.
  4. Print the ranked configs and write the winner to
     $BALL_ARTIFACTS_DIR/xgb_best_params.json.

To make the winner the production config, paste it into train.XGB_PARAMS and
re-run `make train-xgb && make evaluate` to see it on the real hold-out.

Usage:
    python -m ball.pipeline.tune_xgb [--n-iter 40] [--seed 0]
                                     [--days 3,5,7,10,14] [--val-fraction 0.8]
                                     [--dataset PATH]
"""
import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from ball.pipeline import config, features, train

# Search space — discrete choices keep the search seed-reproducible. n_estimators
# is NOT searched: each fit uses early stopping against the validation slice, and
# we report the chosen iteration count so it can be baked into train.XGB_PARAMS.
SEARCH_SPACE = {
    "max_depth": [3, 4, 5, 6, 8],
    "learning_rate": [0.02, 0.03, 0.05, 0.07, 0.1, 0.15],
    "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
    "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
    "min_child_weight": [1, 3, 5, 10, 20],
    "reg_lambda": [0.5, 1.0, 2.0, 5.0, 10.0],
    "gamma": [0.0, 0.5, 1.0, 2.0],
}
EARLY_STOPPING_ROUNDS = 50
MAX_BOOST_ROUNDS = 800  # upper cap; early stopping picks the real count


def sample_config(rng: random.Random) -> dict:
    return {k: rng.choice(v) for k, v in SEARCH_SPACE.items()}


def expanding_folds(dates: np.ndarray, tr: np.ndarray, n_folds: int):
    """Expanding-window temporal CV folds within the train indices `tr`.

    Date-sorted train is cut into n_folds+1 contiguous blocks; fold i trains on
    blocks 0..i and validates on block i+1. Every validation block is later than
    its training data but still earlier than the test hold-out — no leakage."""
    order = tr[np.argsort(dates[tr])]
    blocks = np.array_split(order, n_folds + 1)
    return [(np.concatenate(blocks[: i + 1]), blocks[i + 1]) for i in range(n_folds)]


def score_config(cfg, Xraw, Tdf, folds, score_days, seed):
    """Mean validation ROC-AUC for one config across folds and scored forward
    days, plus the best iteration counts from early stopping. Preprocessing is
    refit per fold on that fold's sub-train only (no val leakage)."""
    from xgboost import XGBClassifier

    aucs, best_iters = [], []
    for sub_tr, val in folds:
        imputer, scaler = SimpleImputer(strategy="median"), StandardScaler()
        Xsub = scaler.fit_transform(imputer.fit_transform(Xraw[sub_tr]))
        Xval = scaler.transform(imputer.transform(Xraw[val]))
        for d in score_days:
            y = Tdf[d].values
            ytr, yval = y[sub_tr], y[val]
            if ytr.sum() < train.MIN_TRAIN_POSITIVES or yval.sum() < 1:
                continue
            pos, neg = int(ytr.sum()), int(len(ytr) - ytr.sum())
            model = XGBClassifier(
                n_estimators=MAX_BOOST_ROUNDS,
                scale_pos_weight=(neg / pos) if pos else 1.0,
                eval_metric="logloss",
                early_stopping_rounds=EARLY_STOPPING_ROUNDS,
                tree_method="hist",
                n_jobs=-1,
                random_state=seed,
                **cfg,
            )
            model.fit(Xsub, ytr, eval_set=[(Xval, yval)], verbose=False)
            proba = model.predict_proba(Xval)[:, 1]
            aucs.append(float(roc_auc_score(yval, proba)))
            best_iters.append(int(model.best_iteration) + 1)  # +1: count, not index
    if not aucs:
        return None
    return float(np.mean(aucs)), best_iters


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n-iter", type=int, default=40, help="random configs to try")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--days", default="3,5,7,10,14",
                    help="forward days to score on ('all' for 1..horizon)")
    ap.add_argument("--folds", type=int, default=3,
                    help="expanding-window temporal CV folds within the train set")
    ap.add_argument("--horizon", type=int, default=config.DEFAULT_FORWARD_DAYS)
    ap.add_argument("--dataset", type=Path, default=None)
    args = ap.parse_args()

    dataset_file = args.dataset or config.dataset_path()
    if not dataset_file.exists():
        raise SystemExit(
            f"No dataset at {dataset_file} — run `python -m ball.pipeline.features` first."
        )
    dataset = train.load_dataset(dataset_file, args.horizon)
    Xdf, Tdf, dates, _ = features.split_dataset(dataset, args.horizon)

    # Temporal split — `te` (the test hold-out) is intentionally never used here.
    tr, _te = train.temporal_split(dates.values)
    folds = expanding_folds(dates.values, tr, args.folds)
    Xraw = Xdf.values

    if args.days == "all":
        score_days = list(range(1, args.horizon + 1))
    else:
        score_days = [int(d) for d in args.days.split(",")]
    fold_sizes = ", ".join(f"{len(s)}->{len(v)}" for s, v in folds)
    print(f"Tuning XGBoost: {args.n_iter} configs, scoring days {score_days}\n"
          f"  {args.folds} expanding temporal folds (sub-train->val): {fold_sizes}\n"
          f"  (test hold-out untouched)")

    rng = random.Random(args.seed)
    results = []
    for i in range(args.n_iter):
        cfg = sample_config(rng)
        scored = score_config(cfg, Xraw, Tdf, folds, score_days, args.seed)
        if scored is None:
            continue
        mean_auc, best_iters = scored
        n_est = int(np.median(best_iters)) if best_iters else MAX_BOOST_ROUNDS
        results.append({"mean_val_auc": mean_auc, "n_estimators": n_est, **cfg})
        print(f"  [{i + 1:>2}/{args.n_iter}] mean val AUC {mean_auc:.4f} "
              f"(n_est~{n_est}) {cfg}")

    if not results:
        raise SystemExit("No config could be scored — too few positives on the chosen days?")

    results.sort(key=lambda r: r["mean_val_auc"], reverse=True)
    print("\n=== Top configs by mean validation ROC-AUC ===")
    ranked = pd.DataFrame(results)
    print(ranked.head(10).to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    best = results[0]
    params = {k: best[k] for k in ("n_estimators", *SEARCH_SPACE.keys())}
    out = config.artifacts_dir() / "xgb_best_params.json"
    out.write_text(json.dumps(params, indent=2))
    print(f"\nBest mean val AUC: {best['mean_val_auc']:.4f}")
    print(f"Wrote winning params to {out}:\n{json.dumps(params, indent=2)}")
    print("\nPaste these into train.XGB_PARAMS, then `make train-xgb && make evaluate`.")


if __name__ == "__main__":
    main()
