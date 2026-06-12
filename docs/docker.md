# Running BALL in Docker

Everything runs from **one shared image** (see `Dockerfile`): the pipeline, the
Streamlit dashboard, and an optional Jupyter service. There is no database
server — the SQLite store is a file on the `ball-db` volume, trained models
live on the `ball-artifacts` volume.

## Quickstart

```bash
docker compose build          # or: make build
make docker-pipeline          # bootstrap → features → train → evaluate → explain
make up                       # dashboard at http://localhost:8501
```

`make docker-pipeline` ends with the evaluation step, which **verifies the
trained models against the frozen reference results**
(`src/ball/pipeline/reference/v2_results_2015-16.csv`) and fails the run if the
per-forward-day ROC-AUCs drift.

## The pieces

| Service | What it does | How to run |
|---|---|---|
| `pipeline` | One-shot: sample CSVs → SQLite → windowed dataset → Y per-day models → evaluation + SHAP | `make docker-pipeline` (or per-step: `make docker-data`, `docker-features`, `docker-train`, `docker-evaluate`, `docker-explain`) |
| `app` | Streamlit risk-curve dashboard | `make up` → http://localhost:8501 |
| `notebook` | Jupyter Lab over the research notebooks (repo mounted at `/app`) | `make notebook` → http://localhost:8888 (token `ball`) |

## Volumes

| Volume | Mounted at | Holds |
|---|---|---|
| `ball-db` | `/data` | `BALL.db` — the SQLite store (`BALL_DB_PATH`) |
| `ball-artifacts` | `/artifacts` | `dataset.csv`, `preprocess.joblib`, `models_logreg.joblib`, `models_gboost.joblib`, `meta.json`, `evaluation.csv`, SHAP outputs (`BALL_ARTIFACTS_DIR`) |

The app only reads what the pipeline wrote — retraining never requires an
image rebuild. `docker compose down` keeps both volumes; add `-v` to start over.

## Where the data comes from

The image **ships the sample data** (one 2015-16 season): the pre-joined model
input (`src/ball/models/injury_prediction/v2/model_input_file.csv`, 17,866
player-games incl. `is_injured`) plus `data/1-nba_api/game_dates.csv` and
`players.csv`. `python -m ball.pipeline.bootstrap` loads them into SQLite, so a
fresh clone needs **no credentials and no network** to reproduce the V2 results.

The **full** data store is Supabase (Postgres) — credentials in `.env` (see
`.env.example`); `connect.py` / `ping.py` talk to it and a daily GitHub Action
keeps the free-tier instance awake. Rebuilding the full relational DB from
sources uses the ETL in `src/ball/scripts/` (NBA stats + tracking via
`nba_api`, Draft Combine anthro, injury-report ETL in
`nba_injury_report_ETL/`); that path needs network access and is documented in
the script docstrings — it is intentionally *not* part of the containerized
reproducible path.

## XGBoost variant (separate stack)

The reference stack above only needs scikit-learn. The optional **XGBoost
comparison** runs from its own image and compose file so it never touches the
base stack — you keep the previous pipeline exactly as-is and run XGBoost
side by side.

```bash
make build-xgb            # build ball-xgb (Dockerfile.xgb, includes xgboost)
make docker-pipeline-xgb  # bootstrap → features → train --model all → evaluate → explain
make up-xgb               # XGBoost dashboard at http://localhost:8502
make docker-tune-xgb      # optional: temporal-CV hyperparameter search in-container
make down-xgb             # stop it (ball-xgb-* volumes survive)
```

What makes it separate (so the two coexist):

| | Base stack | XGBoost stack |
|---|---|---|
| Image | `ball` (`Dockerfile`) | `ball-xgb` (`Dockerfile.xgb`, + `requirements-xgb.txt`) |
| Compose | `docker-compose.yml` | `docker-compose.xgb.yml` (project `ball-xgb`) |
| Train command | `train` (logreg + gboost) | `train --model all` (+ xgboost) |
| App port | 8501 | 8502 |
| Volumes | `ball-db`, `ball-artifacts` | `ball-xgb-db`, `ball-xgb-artifacts` |
| CI | `.github/workflows/ci.yaml` | `.github/workflows/ci-xgb.yaml` |

`evaluate` in the XGBoost stack still verifies logreg/gboost against the frozen
reference and adds an `xgb_auc` column — the XGBoost numbers are reported for
comparison only and are never checked against the reference. The XGBoost image
is larger (the xgboost wheel pulls in CUDA libraries), which is exactly why it
is kept out of the base image.

## Running natively instead (e.g. in the devcontainer)

```bash
make install     # pinned deps + editable package
make pipeline    # same chain, repo-relative paths (data/BALL.db, artifacts/)
make app
make test        # unit tests incl. the temporal-split guard
```

## Reproducibility contract

- Dependencies are **pinned** (`requirements.txt`) and the image's Python
  (3.12.11) matches the version the reference numbers were produced with.
- Training uses a **temporal split** (earliest 80% of dates train). The
  evaluate step and `tests/test_temporal_split.py` both fail loudly if the
  numbers drift or the split goes non-temporal.
- One season of sample data → these are research numbers (GB peaks ≈0.65
  ROC-AUC around days 6–9); treat outputs as relative risk scores, not
  calibrated probabilities.
