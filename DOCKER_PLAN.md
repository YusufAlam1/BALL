# BALL → Dockerized Repo — Build Plan

A plan for taking the existing **BALL** research repo and turning it into a clean,
containerized, reproducible Docker repo — without losing the modeling work already done.

> **Note on this copy:** the original plan said "commit this as `PLAN.md`", but the repo
> already has an (untracked) `plan.md` for the 2026-06-12 presentation; on
> case-insensitive filesystems (Windows/macOS) the two names collide, so this lives at
> `DOCKER_PLAN.md`. Adaptations discovered during Phase 0 recon are flagged inline with
> **[ADAPTED]** markers and logged in `work_done.md`.

---

## 0. The actual starting point

BALL is a working research project, not a blank slate. Any plan has to respect what's already there:

- **Goal:** a player-specific injury *risk curve*. Given the previous **X days** of game data (default 14), predict the probability of injury within each of the next **1…Y days** (default 14) — one model per forward day, producing a day-by-day probability trajectory rather than a single at-risk flag.
- **Data:** four variable categories — movement/load (speed, distance from tracking), performance (minutes, FGA/FGM, rebounds, assists, turnovers, usage %, pace), anthropometrics (Combine measurements), and injury history (prior count, days since last injury, body region, diagnosis, return status). Sources are NBA official stats, tracking, Draft Combine, and injury reports (2021+).
- **[ADAPTED] Storage:** the plan assumed everything lives in a local SQLite DB. In reality the project **migrated to Supabase (Postgres)** and the local `BALL.db` was removed from the repo. The reproducible local path is the sample CSVs (`model_input_file.csv` + `game_dates.csv`), which `ball.pipeline.bootstrap` loads into a local SQLite file — so the "SQLite as a mounted file" architecture below still holds, with Supabase documented as the upstream full-data source.
- **Methodology (V2):** aggregate each X-day window into mean/std/min/max features → build Y per-day binary targets → train Logistic Regression (baseline) and Gradient Boosting (winner) per forward day → evaluate with ROC-AUC. SHAP analysis surfaced workload peaks, distance volatility, age, and usage % as top signals.
- **Current state:** ~93% Jupyter notebooks, ~7% Python. Runs via local venv + `pip install -r requirements.txt`. Not containerized. **[ADAPTED]** A prior session already produced `src/ball/models/injury_prediction/v2/evaluate_v2.py` — a verified, DB-free re-implementation of the V1+V2 evaluation whose outputs (`docs/presentation/v2_results.csv`) are the numbers in the 2026-06-12 presentation. That script is the extraction source of truth for Phase 3, and its numbers are the verification bar.

**So the job is not "build an injury model."** It's: *take a notebook-driven research repo and make its V2 pipeline run reproducibly in Docker, end to end, from data to dashboard.*

---

## 1. The one hard problem: notebooks → runnable modules

Most of the repo is `.ipynb`. You cannot cleanly Dockerize "run this notebook" as a production step. The central refactor is **extracting the V2 pipeline logic into importable Python modules with CLI entry points**, while leaving the exploration notebooks alone.

Concretely, the production path becomes callable like:

```
python -m ball.pipeline.bootstrap                       # sample CSVs -> SQLite
python -m ball.pipeline.features  --lookback 14
python -m ball.pipeline.train     --horizon 14 --model gboost
python -m ball.pipeline.evaluate
streamlit run src/ball/app/app.py
```

Notebooks stay for EDA and remain runnable in a Jupyter container, but the train/feature/eval logic gets a non-notebook home. **Extract, don't rewrite the math.** The goal is to preserve V2's exact behaviour (same features, same per-day targets, same metrics), just in a form Docker can run headlessly.

---

## 2. What to preserve vs. what to change

**Preserve faithfully:**
- The **multi-target, per-forward-day** architecture (Y models → probability curve). Do not collapse it back into a single binary classifier.
- **SQLite** as the local store — file-based, mounted as a volume, no separate database service. (Supabase remains the remote source for full-data rebuilds; don't port the pipeline to it as part of this work.)
- **Time-aware validation.** Splits stay temporal; never introduce a random shuffle.
- Both model families (LogReg baseline + Gradient Boosting) and **ROC-AUC** as the primary metric.

**Change / add (the Dockerization work):**
- Notebook logic → modules (Section 1).
- Pinned, reproducible dependency set.
- Dockerfiles + compose + Makefile.
- A documented, scripted data-acquisition path so a fresh clone can populate the SQLite DB from the sample data in `data/` (full rebuild from Supabase/nba_api documented).
- Containerized Streamlit app.

---

## 3. Target container layout

SQLite means the architecture is light — one image, three services, no DB server:

| Service | Role | Notes |
|---|---|---|
| `pipeline` | Runs bootstrap → feature build → train (Y models) → evaluate | One-shot containers (`make features`, `make train`) |
| `app` | Streamlit risk-curve dashboard | Reads model artifacts + SQLite |
| `notebook` *(optional)* | Jupyter for the research notebooks | So researchers keep working in-container |

Shared via volumes: one for the SQLite `.db`, one for model artifacts (the Y trained models + SHAP outputs).

```
BALL/
├── docker-compose.yml          # NEW
├── Dockerfile                  # NEW (shared base)
├── Makefile                    # NEW
├── pyproject.toml              # NEW — makes ball an installable package
├── requirements.txt            # PIN exact versions
├── .env.example                # exists — extend
├── connect.py / ping.py        # exists — Supabase utilities (keep-alive CI)
├── .github/workflows/          # exists — extend with docker build + smoke test
├── data/                       # exists — sample data for CI/smoke runs
├── docs/                       # exists — add a "Running in Docker" page
├── tests/                      # NEW — unit tests incl. temporal-split guard
└── src/ball/
    ├── db/                     # exists — schema + connection
    ├── scripts/                # exists — extraction/transform/SQL
    ├── exploration/            # exists — leave as notebooks
    ├── models/                 # exists — notebooks become reference
    ├── pipeline/               # NEW — extracted modules + CLI
    │   ├── config.py           #   paths via env (BALL_DB_PATH, BALL_ARTIFACTS_DIR)
    │   ├── bootstrap.py        #   sample CSVs -> SQLite
    │   ├── data.py             #   SQLite data access
    │   ├── features.py         #   X-day aggregation (mean/std/min/max)
    │   ├── targets.py          #   Y per-day binary targets
    │   ├── train.py            #   per-forward-day LogReg + GradientBoosting
    │   ├── evaluate.py         #   ROC-AUC per horizon
    │   └── explain.py          #   SHAP
    └── app/                    # NEW — Streamlit app moved out of models/
        └── app.py
```

---

## 4. Phased build plan

Each phase ends in something runnable.

**Phase 0 — Get it running as-is.** Run the V2 reference (`evaluate_v2.py`) against the sample data and confirm it reproduces `docs/presentation/v2_results.csv`. Inventory the V2 path. Recon only.

**Phase 1 — Pin the environment.** Freeze `requirements.txt` to exact versions. Note system-level deps.

**Phase 2 — Base Docker image.** Single multi-stage `Dockerfile` with pinned deps + `.dockerignore`. Goal: `docker build` succeeds and a shell in the container can run the pipeline CLIs. **[ADAPTED]** This devcontainer has no Docker CLI, so image builds are verified in CI (Phase 8), not locally.

**Phase 3 — Extract the pipeline (the big one).** Pull feature aggregation, target construction, per-day training, and evaluation out of the research code into `src/ball/pipeline/` modules with CLI entry points. Verify output matches the reference V2 results (same ROC-AUC per horizon). Checkpoint heavily.

**Phase 4 — Containerize the pipeline run.** `make features` / `make train` / `make evaluate` each run inside the container, reading SQLite from a mounted volume and writing the Y model artifacts + SHAP outputs to an artifacts volume.

**Phase 5 — Data acquisition path.** Script/document how a clean DB is (re)built: sample CSVs as the fast path for CI and demos; Supabase + `src/ball/scripts/` extraction for the full path. Extend `.env.example`.

**Phase 6 — Dashboard container.** Move the Streamlit POC out of `models/` into `src/ball/app/` (fixing its broken import), have it render the day-by-day probability curve, top drivers, and workload trend lines. Add to compose.

**Phase 7 — Compose + Make.** `docker-compose.yml` wires the pipeline, app, and optional Jupyter services with the SQLite + artifacts volumes. `Makefile` gives one-liners.

**Phase 8 — CI + reproducibility.** Extend `.github/workflows`: lint, a smoke test that runs the pipeline on `data/` samples and asserts artifacts, a `docker build` step, and a test that fails if a non-temporal split sneaks into `train.py`.

---

## 5. Docker specifics for this repo

- **One base image.** pandas / scikit-learn / shap / streamlit are shared across pipeline and app — build once, reuse for each service.
- **SQLite = a mounted file, not a service.** Put the `.db` on a named volume; every container opens the same file.
- **Artifacts volume.** Y trained models + SHAP outputs live on a shared volume so the app reads what the trainer wrote without rebuilding images.
- **Multi-stage** for slimmer images: build wheels in a builder stage, copy into a slim runtime.
- **Secrets in `.env`**, never committed; keep `.env.example` current.

---

## 6. Sequence

0 → run as-is · 1 → pin env · 2 → base image · 3 → extract pipeline (heavy) · 4 → containerize run · 5 → data path · 6 → dashboard · 7 → compose + make · 8 → CI.

The discipline: preserve the model, containerize everything around it, and verify the V2 numbers survive the move out of notebooks.
