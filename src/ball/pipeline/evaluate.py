"""Evaluate the trained per-forward-day models on the temporal hold-out.

Writes per-horizon ROC-AUC (LogReg vs GradientBoosting, plus XGBoost when it
was trained via `train --model all`) to $BALL_ARTIFACTS_DIR/evaluation.csv and,
by default, verifies the lr_auc/gb_auc numbers against the frozen reference (the
values in the 2026-06 presentation). The xgb_auc column is reported for
comparison only — it is never checked against the reference.
ROC-AUC is the primary metric: with a rare positive class it measures
discriminative ability independent of any decision threshold.

gb_auc/test_pos_rate are bit-identical across machines and held to a strict
tolerance; lr_auc rides lbfgs (BLAS kernels vary by CPU) so it gets a looser,
still regression-catching bound. See COLUMN_TOL.

Usage:
    python -m ball.pipeline.evaluate [--dataset PATH] [--reference PATH]
                                     [--no-compare] [--tolerance 1e-6]
                                     [--lr-tolerance 1e-2]
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
# Columns the reference file carries and that we verify against it.
REFERENCE_COLS = ("test_pos_rate", "lr_auc", "gb_auc")

# Per-column reproducibility tolerance.
#   test_pos_rate, gb_auc -> STRICT: the label rate and the tree-based GB model
#     are bit-identical on every machine, so any drift is a real regression.
#   lr_auc -> LOOSE: LogisticRegression's lbfgs solver sums gradients via BLAS
#     kernels that differ by CPU microarchitecture and thread layout. Even
#     single-threaded (we pin threads in train.py/evaluate.py) the per-day AUCs
#     drift ~2-3e-3 between machines — e.g. this devcontainer vs a Codespaces/CI
#     runner. That is solver noise, not a change in the science, so lr_auc gets
#     a looser bound that still trips on a genuine regression (which moves AUC by
#     >>1e-2, e.g. dropping a feature family or breaking the temporal split).
STRICT_TOL = 1e-6
LR_AUC_TOL = 1e-2
COLUMN_TOL = {"test_pos_rate": STRICT_TOL, "lr_auc": LR_AUC_TOL, "gb_auc": STRICT_TOL}


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


def compare(res: pd.DataFrame, reference: Path, tolerances: dict) -> bool:
    ref = pd.read_csv(reference)
    merged = res.merge(ref, on="forward_day", suffixes=("", "_ref"))
    print(f"\nReference comparison vs {reference}:")
    # Verify each reference column this run produced against its own tolerance.
    # A family we didn't train (e.g. logreg-only run, or the extra xgb_auc column
    # the reference doesn't carry) is skipped rather than treated as a mismatch.
    verdicts = {}
    for col in REFERENCE_COLS:
        if col not in res.columns or col not in ref.columns:
            continue
        a, b = merged[col].values, merged[f"{col}_ref"].values
        mask = ~(np.isnan(a) | np.isnan(b))  # compare only where both are present
        if not mask.any():
            continue
        dv = float(np.max(np.abs(a[mask] - b[mask])))
        tol = tolerances[col]
        verdicts[col] = dv <= tol
        flag = "✅" if verdicts[col] else "❌"
        print(f"  max |Δ {col}|: {dv:.2e}  (tol {tol:g})  {flag}")
    if not verdicts:
        print("  (no overlapping reference columns to verify)")
        return True
    ok = all(verdicts.values())
    print(f"  {'✅ PASS' if ok else '❌ FAIL'}")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dataset", type=Path, default=None)
    ap.add_argument("--reference", type=Path, default=config.REFERENCE_RESULTS_CSV,
                    help="frozen results to verify against (default: packaged 2015-16 reference)")
    ap.add_argument("--no-compare", action="store_true")
    ap.add_argument("--tolerance", type=float, default=STRICT_TOL,
                    help="strict bound for the bit-reproducible columns "
                         "(test_pos_rate, gb_auc); default 1e-6")
    ap.add_argument("--lr-tolerance", type=float, default=LR_AUC_TOL,
                    help="looser bound for lr_auc, which lbfgs makes non-bit-exact "
                         "across CPUs; default 1e-2")
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
        tolerances = {"test_pos_rate": args.tolerance, "gb_auc": args.tolerance,
                      "lr_auc": args.lr_tolerance}
        if not compare(res, Path(args.reference), tolerances):
            sys.exit(1)


if __name__ == "__main__":
    main()
