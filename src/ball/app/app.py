"""BALL — injury-risk dashboard.

Renders the signature output: a player's day-by-day injury probability curve
over the next Y days, from their last X days of game load, plus the model's
top SHAP drivers and the player's workload timeline.

Reads trained artifacts from $BALL_ARTIFACTS_DIR (produced by
`python -m ball.pipeline.train`) and player/game data from the SQLite store
at $BALL_DB_PATH (produced by `python -m ball.pipeline.bootstrap`).

Run:  streamlit run src/ball/app/app.py
"""
import json
import re

import joblib
import matplotlib
import pandas as pd
import streamlit as st
from thefuzz import fuzz

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ball.pipeline import config, data, features  # noqa: E402

st.set_page_config(page_title="BALL — Injury Risk", layout="centered")
st.title("BALL — Injury Likelihood Predictor")
st.markdown(
    "Day-by-day injury probability for the next **Y days**, from the previous "
    "**X days** of game data."
)


@st.cache_resource
def load_artifacts():
    art = config.artifacts_dir()
    if not (art / "meta.json").exists():
        return None
    meta = json.loads((art / "meta.json").read_text())
    pre = joblib.load(art / "preprocess.joblib")
    models = {
        fam: joblib.load(art / f"models_{fam}.joblib")
        for fam in meta["model_families"]
        if (art / f"models_{fam}.joblib").exists()
    }
    return meta, pre, models


@st.cache_data
def load_player_list() -> pd.DataFrame:
    with data.connect() as conn:
        return data.load_players(conn)


def fuzzy_match_player(query: str, players_df: pd.DataFrame, threshold: int = 50):
    query = (query or "").strip()
    if not query:
        return None, None, 0
    best_id, best_name, best_score = None, None, 0
    for _, row in players_df.iterrows():
        name = str(row["full_name"]) if pd.notna(row["full_name"]) else ""
        score = max(fuzz.ratio(query.lower(), name.lower()),
                    fuzz.partial_ratio(query.lower(), name.lower()))
        if score >= threshold and score > best_score:
            best_id, best_name, best_score = row["player_id"], name, score
    return best_id, best_name, best_score


try:
    artifacts = load_artifacts()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()
if artifacts is None:
    st.error(
        "No trained models found. Run the pipeline first: "
        "`make data && make features && make train` "
        "(or `python -m ball.pipeline.bootstrap/features/train`)."
    )
    st.stop()
meta, pre, model_sets = artifacts
MAX_FORWARD = meta["horizon"]

col1, col2 = st.columns(2)
with col1:
    player_input = st.text_input(
        "Player name",
        placeholder="e.g. LeBron James, Anthony Davis",
        help="Fuzzy matching — typos and partial names work.",
    )
with col2:
    lookback_days = st.number_input("Lookback window (X days)", 1, 90, 14)

forward_days = st.number_input(
    "Forward window (Y days)", 1, MAX_FORWARD, min(MAX_FORWARD, 14)
)
family = st.radio(
    "Model", [f for f in ("gboost", "xgboost", "logreg") if f in model_sets],
    horizontal=True,
    format_func=lambda f: {"gboost": "Gradient Boosting (V2 winner)",
                           "xgboost": "XGBoost (comparison)",
                           "logreg": "Logistic Regression (baseline)"}[f],
)

if st.button("Predict", type="primary"):
    player_input = re.sub(r"\s+", " ", (player_input or "").strip())[:100]
    if not player_input:
        st.warning("Please enter a player name.")
        st.stop()

    with st.spinner("Finding player…"):
        try:
            players_df = load_player_list()
        except FileNotFoundError as e:
            st.error(str(e))
            st.stop()
        player_id, matched_name, score = fuzzy_match_player(player_input, players_df)

    if player_id is None:
        st.error(f"No player found for '{player_input}'. Try the full name.")
        st.stop()
    if score < 70:
        st.warning(f"Best match: **{matched_name}** (score {score}). Verify this is the "
                   f"intended player.")

    with st.spinner("Building features and predicting…"):
        with data.connect() as conn:
            games = data.load_player_games(conn, player_id)
        if games.empty:
            st.error(f"No game data for {matched_name}.")
            st.stop()
        last_date = games["game_date"].max()
        window = games[games["game_date"] >= last_date - pd.Timedelta(days=lookback_days)]
        present = [c for c in data.RAW_FEATURES if c in games.columns]
        feat = features.aggregate_window(window, present)
        X = (
            pd.DataFrame([feat])
            .reindex(columns=meta["feature_cols"])
            .fillna(0.0)
            .values
        )
        Xs = pre["scaler"].transform(pre["imputer"].transform(X))
        models = model_sets[family]
        probs = {d: float(models[d].predict_proba(Xs)[0, 1])
                 for d in range(1, forward_days + 1) if d in models}

    st.success(
        f"**{matched_name}** — {len(window)} games in the last {lookback_days} days "
        f"(window ending {last_date.date()})"
    )

    # --- the signature output: the day-by-day risk curve ---
    curve = pd.DataFrame(
        {"Days ahead": list(probs), "Injury probability": list(probs.values())}
    ).set_index("Days ahead")
    st.subheader("Risk curve")
    st.line_chart(curve)
    st.dataframe(
        pd.DataFrame(
            {"Day": list(probs), "Injury probability": [f"{p:.2%}" for p in probs.values()]}
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Trained class-balanced on one sample season — read these as **relative risk "
        "scores**, not calibrated probabilities."
    )

    # --- workload trend with injury markers ---
    st.subheader("Workload timeline")
    fig, ax1 = plt.subplots(figsize=(9, 4))
    ax1.plot(games["game_date"], games["minutes"], "-o", ms=2.5, color="steelblue",
             label="Minutes")
    ax1.set_ylabel("Minutes", color="steelblue")
    if "distance" in games.columns:
        ax2 = ax1.twinx()
        ax2.plot(games["game_date"], games["distance"], "-^", ms=2.5, color="seagreen",
                 alpha=0.6, label="Distance")
        ax2.set_ylabel("Distance", color="seagreen")
    for i, d in enumerate(games.loc[games["is_injured"] == 1, "game_date"]):
        ax1.axvline(d, color="crimson", ls="--", lw=1.2,
                    label="Injury event" if i == 0 else None)
    ax1.legend(loc="upper left", fontsize=8)
    fig.autofmt_xdate()
    st.pyplot(fig)
    plt.close(fig)

# --- model-level drivers (from the explain step, if it was run) ---
shap_csv = config.artifacts_dir() / "shap_day7_top_features.csv"
if shap_csv.exists():
    st.subheader("What drives 7-day risk (SHAP, Gradient Boosting)")
    ranking = pd.read_csv(shap_csv).head(12).set_index("feature")
    st.bar_chart(ranking["mean_abs_shap"], horizontal=True)
    st.caption("Mean |SHAP| on the temporal test set — run `make explain` to refresh.")
