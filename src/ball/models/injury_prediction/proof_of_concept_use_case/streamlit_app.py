"""
Streamlit UI for Injury Prediction V2.
- Player name input with fuzzy match and basic string error handling
- X days lookback, Y days forward
- Output: injury likelihood for day 1, 2, 3, ... Y
"""
import re
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import joblib
from thefuzz import fuzz


# Add src to path for ball package (ball lives at src/ball)
V2_DIR = Path(__file__).resolve().parent
SRC_DIR = V2_DIR.parent.parent.parent.parent  # BALL/src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ball.models.injury_prediction.v2.injury_prediction_v2 import (
    load_player_list,
    load_player_lookback,
    fuzzy_match_player,
    aggregate_for_prediction,
)

st.set_page_config(page_title="Injury Prediction V2", layout="centered")
st.title("Injury Likelihood Predictor")
st.markdown("Predict injury probability for the next Y days based on the previous X days of game data.")

# Load artifacts
ARTIFACTS_DIR = V2_DIR / "artifacts"
if not (ARTIFACTS_DIR / "models.joblib").exists():
    st.error(
        "Models not found. Run the training notebook first: "
        "`INJURY_PREDICTION_V2.ipynb` to generate artifacts."
    )
    st.stop()

scaler = joblib.load(ARTIFACTS_DIR / "scaler.joblib")
models = joblib.load(ARTIFACTS_DIR / "models.joblib")
FEATURE_COLS = joblib.load(ARTIFACTS_DIR / "feature_cols.joblib")
MAX_FORWARD_DAYS = joblib.load(ARTIFACTS_DIR / "forward_days.joblib")

# Inputs
col1, col2 = st.columns(2)
with col1:
    player_input = st.text_input(
        "Player name",
        placeholder="e.g. LeBron James, LBJ, Anthony Davis",
        help="Supports fuzzy matching – typos and partial names work.",
    )
with col2:
    lookback_days = st.number_input(
        "Lookback window (X days)",
        min_value=1,
        max_value=90,
        value=14,
        help="Use game data from the previous X days.",
    )

forward_days = st.number_input(
    "Forward window (Y days)",
    min_value=1,
    max_value=min(MAX_FORWARD_DAYS, 30),
    value=min(7, MAX_FORWARD_DAYS),
    help="Predict injury likelihood for each day from 1 to Y.",
)

# Basic string error handling
def sanitize_player_input(s: str) -> str:
    if not s or not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = s[:100]
    return s

player_input = sanitize_player_input(player_input)

if st.button("Predict", type="primary"):
    if not player_input:
        st.warning("Please enter a player name.")
        st.stop()

    with st.spinner("Finding player..."):
        players_df = load_player_list()
        player_id, matched_name, score = fuzzy_match_player(player_input, players_df, threshold=50)

    if player_id is None:
        st.error(f"No player found for '{player_input}'. Try a different spelling or full name.")
        if len(player_input) >= 3:
            st.info("Suggestions: Check spelling or use the player's full name.")
        st.stop()

    if score < 70:
        st.warning(f"Best match: **{matched_name}** (score: {score}). Verify this is the intended player.")

    with st.spinner("Loading game data and predicting..."):
        games_df = load_player_lookback(player_id, lookback_days)
        if games_df.empty:
            st.error(
                f"No game data found for {matched_name} in the last {lookback_days} days. "
                "Try increasing the lookback window."
            )
            st.stop()

        feat_row = aggregate_for_prediction(games_df, FEATURE_COLS)
        if feat_row is None:
            st.error("Could not build features from game data.")
            st.stop()

        X = pd.DataFrame([feat_row])
        for c in FEATURE_COLS:
            if c not in X.columns:
                X[c] = 0.0
        X = X[FEATURE_COLS]
        X_scaled = scaler.transform(X)

        probs = {}
        for d in range(1, forward_days + 1):
            if d in models:
                p = models[d].predict_proba(X_scaled)[0, 1]
                probs[d] = float(p)
            else:
                probs[d] = None

    st.success(f"Predictions for **{matched_name}** (based on last {lookback_days} days)")

    results = []
    for d in range(1, forward_days + 1):
        p = probs.get(d)
        if p is not None:
            results.append({"Day": d, "Injury probability": f"{p:.2%}"})
    df = pd.DataFrame(results)

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Bar chart
    chart_data = pd.DataFrame({
        "Day": list(probs.keys()),
        "Probability": [probs[d] or 0 for d in probs],
    })
    st.bar_chart(chart_data.set_index("Day"))
