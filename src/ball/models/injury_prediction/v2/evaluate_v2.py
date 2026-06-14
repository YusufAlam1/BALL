"""
Reproducible evaluation of BALL injury-prediction models — for the Friday presentation.

Runs entirely from local CSVs (no database required):
  - src/ball/models/injury_prediction/v2/model_input_file.csv  (game-level rows + is_injured)
  - data/1-nba_api/game_dates.csv                               (game_id -> game_date)

Produces:
  1. V1 game-level classification baseline (the "naive" approach the README pivots away from)
from threadpoolctl import threadpool_limits
  2. V2 rolling-window models: per-forward-day ROC-AUC for LogReg vs GradientBoosting
  3. Figures saved to docs/presentation/figures/ for direct drop-in to slides
  4. A results table printed to stdout and written to docs/presentation/v2_results.csv

Usage:
    python src/ball/models/injury_prediction/v2/evaluate_v2.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    average_precision_score,
    precision_score,
    recall_score,
)

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
THIS = Path(__file__).resolve()
REPO = THIS.parents[5]  # v2 -> injury_prediction -> models -> ball -> src -> REPO
CSV = THIS.parent / "model_input_file.csv"
GAME_DATES = REPO / "data" / "1-nba_api" / "game_dates.csv"
PRESENTATION_DIR = REPO / "docs" / "presentation"
FIG_DIR = PRESENTATION_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

LOOKBACK_DAYS = 14
FORWARD_DAYS = 14
RANDOM_STATE = 42

# Raw game-level feature columns (lowercased) we aggregate over the lookback window
RAW_FEATURES = [
    "age", "speed", "distance", "height_wo_shoes", "weight", "wingspan",
    "standing_reach", "body_fat_pct", "hand_length", "hand_width",
    "minutes", "usagepercentage", "pace", "possessions",
]
AGG_STATS = ["mean", "std", "min", "max"]


def parse_minutes(val):
    """MM:SS -> float minutes."""
    if pd.isna(val) or val == "":
        return np.nan
    s = str(val).strip()
    if ":" in s:
        m, sec = s.split(":")[:2]
        try:
            return float(m) + float(sec) / 60.0
        except ValueError:
            return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def load_data():
    df = pd.read_csv(CSV)
    df.columns = [c.lower() for c in df.columns]
    gd = pd.read_csv(GAME_DATES)
    gd.columns = [c.lower() for c in gd.columns]
    gd["game_date"] = pd.to_datetime(gd["game_date"])
    df = df.merge(gd, on="game_id", how="left")
    df["minutes"] = df["minutes"].apply(parse_minutes)
    for c in RAW_FEATURES:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["game_date"]).sort_values(["player_id", "game_date"]).reset_index(drop=True)
    return df


# ----------------------------------------------------------------------------
# V1: game-level classification (the naive baseline)
# ----------------------------------------------------------------------------
def evaluate_v1(df):
    feats = [c for c in RAW_FEATURES if c in df.columns]
    X = df[feats].values
    y = df["is_injured"].astype(int).values

    # temporal split: earliest 80% train, latest 20% test
    order = np.argsort(df["game_date"].values)
    cut = int(len(order) * 0.8)
    tr, te = order[:cut], order[cut:]

    imp = SimpleImputer(strategy="median")
    sc = StandardScaler()
    Xtr = sc.fit_transform(imp.fit_transform(X[tr]))
    Xte = sc.transform(imp.transform(X[te]))

    clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)
    clf.fit(Xtr, y[tr])
    p = clf.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(y[te], p)
    pred = (p >= 0.5).astype(int)
    prec = precision_score(y[te], pred, zero_division=0)
    rec = recall_score(y[te], pred, zero_division=0)

    print("\n=== V1: game-level binary classification ===")
    print(f"  base rate (positives): {y.mean():.2%}  ({int(y.sum())}/{len(y)} games)")
    print(f"  ROC-AUC:   {auc:.3f}")
    print(f"  Precision: {prec:.3f}   Recall: {rec:.3f}  (threshold 0.5)")
    return {"base_rate": float(y.mean()), "roc_auc": float(auc), "precision": float(prec), "recall": float(rec)}


# ----------------------------------------------------------------------------
# V2: rolling-window features + per-forward-day targets
# ----------------------------------------------------------------------------
def build_v2(df):
    feat_cols = []
    for stat in AGG_STATS:
        for c in RAW_FEATURES:
            if c in df.columns:
                feat_cols.append(f"{c}_{stat}")

    rows, targets, dates = [], [], []
    present = [c for c in RAW_FEATURES if c in df.columns]

    for pid, grp in df.groupby("player_id"):
        grp = grp.sort_values("game_date").reset_index(drop=True)
        injury_dates = grp.loc[grp["is_injured"] == 1, "game_date"].tolist()
        gdates = grp["game_date"].values
        for i in range(len(grp)):
            row_date = grp.iloc[i]["game_date"]
            start = row_date - pd.Timedelta(days=LOOKBACK_DAYS)
            mask = (grp["game_date"] <= row_date) & (grp["game_date"] >= start)
            window = grp.loc[mask, present]
            if window.empty:
                continue
            agg = window.agg(AGG_STATS)  # rows=stats, cols=features
            feat = {}
            for stat in AGG_STATS:
                for c in present:
                    v = agg.loc[stat, c]
                    feat[f"{c}_{stat}"] = 0.0 if pd.isna(v) else float(v)
            tgt = {}
            for d in range(1, FORWARD_DAYS + 1):
                end = row_date + pd.Timedelta(days=d)
                tgt[d] = int(any((idt > row_date) and (idt <= end) for idt in injury_dates))
            rows.append(feat)
            targets.append(tgt)
            dates.append(row_date)

    Xdf = pd.DataFrame(rows).reindex(columns=feat_cols).fillna(0.0)
    Tdf = pd.DataFrame(targets)
    dser = pd.Series(dates, name="game_date")
    return Xdf, Tdf, dser, feat_cols


def evaluate_v2(Xdf, Tdf, dser):
    order = np.argsort(dser.values)
    cut = int(len(order) * 0.8)
    tr, te = order[:cut], order[cut:]

    imp = SimpleImputer(strategy="median")
    sc = StandardScaler()
    Xtr = sc.fit_transform(imp.fit_transform(Xdf.values[tr]))
    Xte = sc.transform(imp.transform(Xdf.values[te]))

    results = []
    for d in range(1, FORWARD_DAYS + 1):
        y = Tdf[d].values
        ytr, yte = y[tr], y[te]
        row = {"forward_day": d, "test_pos_rate": float(yte.mean())}
        if ytr.sum() < 5 or yte.sum() < 1:
            row.update({"lr_auc": np.nan, "gb_auc": np.nan})
            results.append(row)
            continue
        with threadpool_limits(limits=1):
            lr = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)
            lr.fit(Xtr, ytr)
        row["lr_auc"] = float(roc_auc_score(yte, lr.predict_proba(Xte)[:, 1]))

        gb = GradientBoostingClassifier(random_state=RANDOM_STATE)
        gb.fit(Xtr, ytr)
        row["gb_auc"] = float(roc_auc_score(yte, gb.predict_proba(Xte)[:, 1]))
        results.append(row)

    res = pd.DataFrame(results)
    print("\n=== V2: rolling-window per-forward-day ROC-AUC ===")
    print(res.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    res.to_csv(PRESENTATION_DIR / "v2_results.csv", index=False)
    return res, (imp, sc, tr, te)


# ----------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------
def fig_auc_curve(res):
    plt.figure(figsize=(8, 5))
    plt.plot(res["forward_day"], res["lr_auc"], "o-", label="Logistic Regression")
    plt.plot(res["forward_day"], res["gb_auc"], "s-", label="Gradient Boosting")
    plt.axhline(0.5, ls="--", c="gray", lw=1, label="Random (0.5)")
    plt.xlabel("Forward day (injury within d days)")
    plt.ylabel("ROC-AUC (temporal hold-out)")
    plt.title("V2 Rolling-Window: ROC-AUC across the 14-day horizon")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig1_auc_vs_forward_day.png", dpi=150)
    plt.close()


def fig_player_curve(df, Xdf, Tdf, dser, feat_cols, imp, sc, tr):
    """Probability curve for a sample player's most recent observation."""
    lr_models = {}
    Xtr = sc.transform(imp.transform(Xdf.values[tr]))
    for d in range(1, FORWARD_DAYS + 1):
        y = Tdf[d].values[tr]
        if y.sum() < 5:
            continue
        m = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)
        m.fit(Xtr, y)
        lr_models[d] = m

    # pick the player with the most games for a clean curve
    pid = df["player_id"].value_counts().idxmax()
    sub = df[df["player_id"] == pid].sort_values("game_date")
    last_date = sub["game_date"].max()
    start = last_date - pd.Timedelta(days=LOOKBACK_DAYS)
    window = sub[(sub["game_date"] <= last_date) & (sub["game_date"] >= start)]
    present = [c for c in RAW_FEATURES if c in df.columns]
    agg = window[present].agg(AGG_STATS)
    feat = {}
    for stat in AGG_STATS:
        for c in present:
            v = agg.loc[stat, c]
            feat[f"{c}_{stat}"] = 0.0 if pd.isna(v) else float(v)
    x = pd.DataFrame([feat]).reindex(columns=feat_cols).fillna(0.0).values
    x = sc.transform(imp.transform(x))

    days = sorted(lr_models)
    probs = [lr_models[d].predict_proba(x)[0, 1] for d in days]
    plt.figure(figsize=(8, 5))
    plt.plot(days, probs, "o-", color="crimson")
    plt.fill_between(days, probs, alpha=0.15, color="crimson")
    plt.xlabel("Days ahead")
    plt.ylabel("Predicted injury probability")
    plt.title(f"Signature output: day-by-day injury-risk curve\n(player_id {pid}, last {LOOKBACK_DAYS} days of load)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig3_player_probability_curve.png", dpi=150)
    plt.close()


def fig_feature_importance(Xdf, Tdf, feat_cols, imp, sc, tr):
    """GB feature importances for a mid-horizon target (day 7)."""
    target_day = 7
    y = Tdf[target_day].values[tr]
    Xtr = sc.transform(imp.transform(Xdf.values[tr]))
    gb = GradientBoostingClassifier(random_state=RANDOM_STATE)
    gb.fit(Xtr, y)
    imp_s = pd.Series(gb.feature_importances_, index=feat_cols).sort_values(ascending=True).tail(15)
    plt.figure(figsize=(8, 6))
    imp_s.plot(kind="barh", color="steelblue")
    plt.xlabel("Gradient Boosting importance")
    plt.title(f"Top features driving {target_day}-day injury risk")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig2_feature_importance.png", dpi=150)
    plt.close()


def fig_base_rate(res):
    plt.figure(figsize=(8, 5))
    plt.bar(res["forward_day"], res["test_pos_rate"] * 100, color="darkorange")
    plt.xlabel("Forward day")
    plt.ylabel("Injury rate in window (%)")
    plt.title("Why the horizon matters: positive-class rate grows with the window")
    plt.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig4_positive_rate_by_horizon.png", dpi=150)
    plt.close()


def fig_shap_beeswarm(Xdf, Tdf, feat_cols, imp, sc, tr, te):
    """SHAP beeswarm for the GB model on the 7-day target (test set)."""
    import shap

    target_day = 7
    ytr = Tdf[target_day].values[tr]
    Xtr = sc.transform(imp.transform(Xdf.values[tr]))
    Xte = sc.transform(imp.transform(Xdf.values[te]))
    gb = GradientBoostingClassifier(random_state=RANDOM_STATE)
    gb.fit(Xtr, ytr)

    # sample test rows for a readable plot
    rng = np.random.RandomState(RANDOM_STATE)
    n = min(800, Xte.shape[0])
    idx = rng.choice(Xte.shape[0], size=n, replace=False)
    Xs = pd.DataFrame(Xte[idx], columns=feat_cols)

    explainer = shap.TreeExplainer(gb)
    shap_values = explainer.shap_values(Xs)

    plt.figure()
    shap.summary_plot(shap_values, Xs, max_display=15, show=False)
    plt.title(f"SHAP: feature impact on {target_day}-day injury risk (GB)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig2b_shap_beeswarm.png", dpi=150, bbox_inches="tight")
    plt.close()


def fig_workload_timeline(df):
    """Game-by-game workload for one player with actual injury events overlaid."""
    inj_counts = df[df["is_injured"] == 1]["player_id"].value_counts()
    inj_counts = inj_counts[inj_counts >= 2]
    if inj_counts.empty:
        pid = df["player_id"].value_counts().idxmax()
    else:
        # among multi-injury players, pick the one with the most games (densest timeline)
        cand = inj_counts.index
        pid = df[df["player_id"].isin(cand)]["player_id"].value_counts().idxmax()

    sub = df[df["player_id"] == pid].sort_values("game_date")
    inj_dates = sub.loc[sub["is_injured"] == 1, "game_date"]

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(sub["game_date"], sub["minutes"], "-o", ms=3, color="steelblue", label="Minutes played")
    ax1.set_ylabel("Minutes played", color="steelblue")
    ax1.tick_params(axis="y", labelcolor="steelblue")

    ax2 = ax1.twinx()
    ax2.plot(sub["game_date"], sub["distance"], "-^", ms=3, color="seagreen", alpha=0.6, label="Distance")
    ax2.set_ylabel("Distance covered", color="seagreen")
    ax2.tick_params(axis="y", labelcolor="seagreen")

    for i, d in enumerate(inj_dates):
        ax1.axvline(d, color="crimson", ls="--", lw=1.5, label="Injury event" if i == 0 else None)

    ax1.set_xlabel("Game date")
    ax1.set_title(f"Workload trend with injury events (player_id {pid})")
    lines, labels = ax1.get_legend_handles_labels()
    l2, lab2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + l2, labels + lab2, loc="upper left", fontsize=8)
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "fig5_workload_timeline.png", dpi=150)
    plt.close()


def main():
    print(f"Repo: {REPO}")
    df = load_data()
    print(f"Loaded {len(df)} player-game rows, {df['player_id'].nunique()} players, "
          f"{df['game_date'].min().date()} -> {df['game_date'].max().date()}")

    v1 = evaluate_v1(df)

    Xdf, Tdf, dser, feat_cols = build_v2(df)
    print(f"\nBuilt V2 design matrix: {Xdf.shape[0]} observations x {Xdf.shape[1]} features")
    res, (imp, sc, tr, te) = evaluate_v2(Xdf, Tdf, dser)

    fig_auc_curve(res)
    fig_base_rate(res)
    fig_feature_importance(Xdf, Tdf, feat_cols, imp, sc, tr)
    fig_shap_beeswarm(Xdf, Tdf, feat_cols, imp, sc, tr, te)
    fig_player_curve(df, Xdf, Tdf, dser, feat_cols, imp, sc, tr)
    fig_workload_timeline(df)

    print(f"\nFigures written to {FIG_DIR}")
    print("  fig1_auc_vs_forward_day.png")
    print("  fig2_feature_importance.png")
    print("  fig2b_shap_beeswarm.png")
    print("  fig3_player_probability_curve.png")
    print("  fig4_positive_rate_by_horizon.png")
    print("  fig5_workload_timeline.png")
    print("  v2_results.csv")


if __name__ == "__main__":
    main()
