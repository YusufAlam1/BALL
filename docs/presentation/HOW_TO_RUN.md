# How to run the BALL presentation materials

Everything for the Friday talk lives in this folder (`docs/presentation/`):

| File | What it is |
|------|------------|
| `outline.md` | The slide-by-slide deck outline with speaker notes and Q&A prep |
| `figures/*.png` | The six figures, ready to drop into slides |
| `v2_results.csv` | Per-forward-day ROC-AUC table (LR vs GB) |
| `HOW_TO_RUN.md` | This file |

All figures and numbers are produced by **one script** and require **no database** — it reads
two local CSVs that already ship in the repo.

---

## 1. What generates everything

```
src/ball/models/injury_prediction/v2/evaluate_v2.py
```

It reads:
- `src/ball/models/injury_prediction/v2/model_input_file.csv` — game-level rows + `is_injured`
- `data/1-nba_api/game_dates.csv` — maps `game_id` → `game_date` (supplies the dates the
  rolling-window model needs)

It writes:
- `docs/presentation/figures/fig1..fig5*.png`
- `docs/presentation/v2_results.csv`

> Note: it **retrains the models from scratch** each run rather than loading the saved
> `artifacts/*.joblib`, because those were pickled with an older scikit-learn and no longer
> unpickle. Retraining keeps the results fully reproducible. Runtime is ~2–3 minutes.

---

## 2. One-time setup

From the repo root (`/workspaces/BALL`):

```bash
# (optional) virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate

# install dependencies
pip install -r requirements.txt
```

The script only needs: `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `shap` — all already in
`requirements.txt`.

---

## 3. Run it

From the repo root:

```bash
python src/ball/models/injury_prediction/v2/evaluate_v2.py
```

You'll see the V1 baseline stats and the full V2 per-day ROC-AUC table printed, then a list of the
figures written. Re-running overwrites the figures and `v2_results.csv` in place.

---

## 4. What each figure is (and which slide it belongs to)

| File | Slide | Shows |
|------|-------|-------|
| `figures/fig4_positive_rate_by_horizon.png` | 8 | Injury rate grows 0.25% → 4.5% across the horizon (the imbalance story) |
| `figures/fig1_auc_vs_forward_day.png` | 9 | **Headline**: ROC-AUC per forward day, Gradient Boosting vs Logistic Regression |
| `figures/fig2b_shap_beeswarm.png` | 10 | SHAP: which features drive 7-day risk (backup: `fig2_feature_importance.png`) |
| `figures/fig5_workload_timeline.png` | 11 | One player's per-game minutes/distance with injury events marked |
| `figures/fig3_player_probability_curve.png` | 12 | **Signature output**: a player's day-by-day risk curve |

The headline numbers (V1 ROC-AUC 0.659 / precision 2.1%; V2 GB peak AUC ≈ 0.65) and the figures
are cross-referenced slide-by-slide in `outline.md`.

---

## 5. Tuning knobs

Open `evaluate_v2.py` and edit the constants near the top:

```python
LOOKBACK_DAYS = 14   # X: size of the lookback window
FORWARD_DAYS  = 14   # Y: how many forward-day targets / curve length
RANDOM_STATE  = 42   # reproducibility seed
```

Change them and re-run to regenerate every figure and the results table with the new settings.

---

## 6. Troubleshooting

- **`ModuleNotFoundError: No module named 'shap'`** (or matplotlib, etc.) → `pip install -r requirements.txt`.
- **`FileNotFoundError` on a CSV** → run from the repo root, or check the two input CSVs listed in §1 exist.
- **Plots look different than the deck** → confirm `RANDOM_STATE = 42` and that you're on the shipped CSVs.
- **Want to reach the live Supabase data instead of CSVs** → out of scope for the talk; see the
  deferred items in the root `plan.md`.
