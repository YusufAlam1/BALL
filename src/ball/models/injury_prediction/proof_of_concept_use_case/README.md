# Injury Prediction V2

Predicts injury probability for the next **Y** days based on the previous **X** days of game data.

## Setup

```bash
pip install streamlit thefuzz scikit-learn joblib pandas
```

## 1. Train the model

Run all cells in `INJURY_PREDICTION_V2.ipynb`. This will:

- Load game-level data from `BALL.db`
- Build X-day lookback aggregates (mean, std, min, max) for all numeric features
- Create Y-day forward targets (injured within 1 day, 2 days, ... Y days)
- Train models (Logistic Regression + GradientBoosting) for each forward day
- Save artifacts to `artifacts/`

## 2. Run the Streamlit UI

```bash
cd src/ball/models/injury_prediction/proof_of_concept_use_case
streamlit run streamlit_app.py
```

Or from project root:

```bash
streamlit run src/ball/models/injury_prediction/proof_of_model_use_case/streamlit_app.py
```

## Usage

1. **Player name**: Enter a player (fuzzy match, e.g. "LeBron", "LBJ", "Anthony Davis")
2. **Lookback (X days)**: Use game data from the previous X days
3. **Forward (Y days)**: Output injury likelihood for days 1, 2, 3, ... Y

## SQL Queries

| File | Purpose |
|------|---------|
| `model_input_base.sql` | Base game-level features for training |
| `injury_dates.sql` | Injury events (relinquished) |
| `player_list.sql` | Players for fuzzy search |
| `player_lookback.sql` | Player-specific games in lookback window |
