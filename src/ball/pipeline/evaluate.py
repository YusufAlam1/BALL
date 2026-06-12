"""Evaluate the trained per-forward-day models on the temporal hold-out.

Writes per-horizon ROC-AUC (LogReg vs GradientBoosting, plus XGBoost when it
was trained via `train --model all`) to $BALL_ARTIFACTS_DIR/evaluation.csv and,
by default, verifies the lr_auc/gb_auc numbers against the frozen reference (the
values in the 2026-06 presentation). The xgb_auc column is reported for
comparison only — it is never checked against the reference.
ROC-AUC is the primary metric: with a rare positive class it measures
discriminative ability independent of any decision threshold.

Usage:
    python -m ball.pipeline.evaluate [--dataset PATH] [--reference PATH]
                                     [--no-compare] [--tolerance 1e-6]
"""
import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from ball.pipeline import config, features, train

# Ordered family -> AUC column name. logreg/gboost match the frozen reference
# CSV; xgboost adds an extra column for side-by-side comparison only.
FAMILY_AUC_COL = [("logreg", "lr_auc"), ("gboost", "gb_auc"), ("xgboost", "xgb_auc")]
# Columns the reference file carries and that must reproduce exactly.
REFERENCE_COLS = ("test_pos_rate", "lr_auc", "gb_auc")


def evaluate(dataset: pd.DataFrame, art: Path) -> pd.DataFrame:
    meta = json.loads((art / "meta.json").read_text())
    horizon = meta["horizon"]
    Xdf, Tdf, dates, feat_cols = features.split_dataset(dataset, horizon)
    if feat_cols != meta["feature_cols"]:
        raise SystemExit("Dataset feature columns do not match the trained artifacts — "
                         "rerun features + train together.")
    if len(dates) != meta["n_observations"]:
        raise SystemExit(f"Dataset has {len(dates)} rows but models were trained on "
                         f"{meta['n_observations']} — rerun train.")
    tr, te = train.temporal_split(dates.values, meta["train_fraction"])

    pre = joblib.load(art / "preprocess.joblib")
    Xte = pre["scaler"].transform(pre["imputer"].transform(Xdf.values[te]))
    model_sets = {
        fam: joblib.load(art / f"models_{fam}.joblib")
        for fam in meta["model_families"]
        if (art / f"models_{fam}.joblib").exists()
    }

    # Report a column per trained family, keeping lr_auc/gb_auc first so the
    # output stays comparable with the reference CSV; xgb_auc is appended only
    # when the xgboost family was trained.
    families = [(fam, key) for fam, key in FAMILY_AUC_COL if fam in meta["model_families"]]
    results = []
    # Single-threaded BLAS for predict_proba so the scored probabilities — and
    # therefore the ROC-AUC ranking — are identical regardless of core count,
    # matching the single-threaded fits in train.py (see the note there).
    with threadpool_limits(limits=1):
        for d in range(1, horizon + 1):
            yte = Tdf[d].values[te]
            row = {"forward_day": d, "test_pos_rate": float(yte.mean())}
            for fam, key in families:
                model = model_sets.get(fam, {}).get(d)
                row[key] = (
                    float(roc_auc_score(yte, model.predict_proba(Xte)[:, 1]))
                    if model is not None and yte.sum() >= 1
                    else np.nan
                )
            results.append(row)
    return pd.DataFrame(results)


def compare(res: pd.DataFrame, reference: Path, tolerance: float) -> bool:
    ref = pd.read_csv(reference)
    merged = res.merge(ref, on="forward_day", suffixes=("", "_ref"))
    diffs = {}
    # Only verify reference columns that this run actually produced. A family
    # we didn't train (e.g. logreg-only run, or the extra xgb_auc column that
    # the reference doesn't carry) is skipped rather than treated as a mismatch.
    for col in REFERENCE_COLS:
        if col not in res.columns or col not in ref.columns:
            continue
        a, b = merged[col].values, merged[f"{col}_ref"].values
        mask = ~(np.isnan(a) | np.isnan(b))  # compare only where both are present
        if mask.any():
            diffs[col] = float(np.max(np.abs(a[mask] - b[mask])))
    print(f"\nReference comparison vs {reference}:")
    if not diffs:
        print("  (no overlapping reference columns to verify)")
        return True
    for col, dv in diffs.items():
        print(f"  max |Δ {col}|: {dv:.2e}")
    worst = max(diffs.values())
    ok = worst <= tolerance
    print(f"  {'✅ PASS' if ok else '❌ FAIL'} (tolerance {tolerance:g})")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dataset", type=Path, default=None)
    ap.add_argument("--reference", type=Path, default=config.REFERENCE_RESULTS_CSV,
                    help="frozen results to verify against (default: packaged 2015-16 reference)")
    ap.add_argument("--no-compare", action="store_true")
    ap.add_argument("--tolerance", type=float, default=1e-6)
    args = ap.parse_args()

    dataset_file = args.dataset or config.dataset_path()
    art = config.artifacts_dir()
    if not (art / "meta.json").exists():
        raise SystemExit(f"No trained models in {art} — run `python -m ball.pipeline.train` first.")
    meta = json.loads((art / "meta.json").read_text())
    dataset = train.load_dataset(dataset_file, meta["horizon"])

    res = evaluate(dataset, art)
    print("\n=== V2: rolling-window per-forward-day ROC-AUC (temporal hold-out) ===")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    out = art / "evaluation.csv"
    res.to_csv(out, index=False)
    print(f"\nWrote {out}")

    if not args.no_compare and args.reference and Path(args.reference).exists():
        if not compare(res, Path(args.reference), args.tolerance):
            sys.exit(1)


if __name__ == "__main__":
    main()
