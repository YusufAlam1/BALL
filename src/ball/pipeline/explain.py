"""SHAP feature attribution for one forward-day Gradient Boosting model.

Writes to $BALL_ARTIFACTS_DIR:
    shap_day<d>_beeswarm.png      beeswarm of per-feature impact (test sample)
    shap_day<d>_top_features.csv  mean |SHAP| ranking

Usage:
    python -m ball.pipeline.explain [--day 7] [--sample 800] [--dataset PATH]
"""
import argparse
import json
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ball.pipeline import config, features, train  # noqa: E402


def explain(dataset: pd.DataFrame, art: Path, day: int, sample: int) -> Path:
    import shap  # heavy import — keep local

    meta = json.loads((art / "meta.json").read_text())
    Xdf, Tdf, dates, feat_cols = features.split_dataset(dataset, meta["horizon"])
    tr, te = train.temporal_split(dates.values, meta["train_fraction"])
    pre = joblib.load(art / "preprocess.joblib")
    Xte = pre["scaler"].transform(pre["imputer"].transform(Xdf.values[te]))

    models = joblib.load(art / "models_gboost.joblib")
    if day not in models:
        raise SystemExit(f"No gboost model for forward day {day} "
                         f"(available: {sorted(models)}). Train with --model both|gboost.")

    rng = np.random.RandomState(config.RANDOM_STATE)
    n = min(sample, Xte.shape[0])
    idx = rng.choice(Xte.shape[0], size=n, replace=False)
    Xs = pd.DataFrame(Xte[idx], columns=feat_cols)

    explainer = shap.TreeExplainer(models[day])
    shap_values = explainer.shap_values(Xs)

    plt.figure()
    shap.summary_plot(shap_values, Xs, max_display=15, show=False)
    plt.title(f"SHAP: feature impact on {day}-day injury risk (GradientBoosting)")
    plt.tight_layout()
    png = art / f"shap_day{day}_beeswarm.png"
    plt.savefig(png, dpi=150, bbox_inches="tight")
    plt.close()

    ranking = (
        pd.DataFrame({"feature": feat_cols, "mean_abs_shap": np.abs(shap_values).mean(axis=0)})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    csv = art / f"shap_day{day}_top_features.csv"
    ranking.to_csv(csv, index=False)
    print(ranking.head(10).to_string(index=False))
    print(f"\nWrote {png}\nWrote {csv}")
    return png


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--day", type=int, default=7, help="forward day to explain (default 7)")
    ap.add_argument("--sample", type=int, default=800, help="test rows sampled for SHAP")
    ap.add_argument("--dataset", type=Path, default=None)
    args = ap.parse_args()

    art = config.artifacts_dir()
    if not (art / "meta.json").exists():
        raise SystemExit(f"No trained models in {art} — run `python -m ball.pipeline.train` first.")
    meta = json.loads((art / "meta.json").read_text())
    dataset = train.load_dataset(args.dataset or config.dataset_path(), meta["horizon"])
    explain(dataset, config.artifacts_dir(), args.day, args.sample)


if __name__ == "__main__":
    main()
