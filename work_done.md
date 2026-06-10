# work_done.md — Dockerization work log

Running log of the work to containerize BALL per `DOCKER_PLAN.md`.
Branch: `dockerize`. Each phase ends in a commit.

---

## Phase 0 — Recon & run as-is (2026-06-10)

### What was found

- **The repo migrated to Supabase/Postgres; the local SQLite `BALL.db` is gone.**
  `connect.py`/`ping.py` are Supabase utilities (a daily GitHub Action pings it to
  prevent free-tier pausing). The plan's "keep SQLite, mount the .db" architecture is
  preserved by *bootstrapping* a local SQLite file from the sample CSVs; Supabase stays
  the upstream source. Flagged as **[ADAPTED]** in `DOCKER_PLAN.md`.
- **A previous session (2026-06-08) already did part of Phase 3's work**:
  `src/ball/models/injury_prediction/v2/evaluate_v2.py` re-implements the V1 baseline +
  V2 rolling-window evaluation from CSVs (no DB), with a temporal 80/20 split. Its
  outputs are the numbers in the Friday 2026-06-12 presentation
  (`docs/presentation/v2_results.csv`). That script is the **extraction source of
  truth** and its per-day ROC-AUCs are the **verification bar** for the pipeline.
- **The V2 data path**: `src/ball/models/injury_prediction/v2/model_input_file.csv`
  (17,866 player-game rows, 2015-16 season, features + `is_injured`) +
  `data/1-nba_api/game_dates.csv`. The original SQL (`model_input_base.sql` etc. in
  `proof_of_concept_use_case/`) produced that CSV from the old SQLite DB.
- **The official V2 notebook (`INJURY_PREDICTION_V2.ipynb`) uses a random stratified
  split**; `evaluate_v2.py` uses the temporal split. The plan mandates temporal, so the
  pipeline uses the temporal split (= the presentation numbers).
- **The Streamlit POC is broken as-is**: `streamlit_app.py` imports
  `ball.models.injury_prediction.v2.injury_prediction_v2`, but that module lives in
  `proof_of_concept_use_case/`. Fixed in Phase 6 by moving the app to `src/ball/app/`.
  Also: `streamlit` was not even installed/pinned.
- **`fixed_window.ipynb` (v2) contains only `import pandas as pd`** — the real V2
  logic lives in `INJURY_PREDICTION_V2.ipynb` + `injury_prediction_v2.py` +
  `evaluate_v2.py`.
- **No Docker CLI in this devcontainer** — Dockerfiles/compose are authored here and
  verified by the CI `docker build` + smoke test (Phase 8), not locally.
- **Line endings were a mess**: 48 files committed with CRLF, 47 with LF, and the
  whole working tree had drifted to CRLF (showing 47 phantom "modified" files).
  Normalized everything to LF + added `.gitattributes` (commit `12eca55`). CRLF inside
  images breaks shell scripts, so this is a real Docker prerequisite, not just tidying.
- **Pre-existing untracked files left alone** (they're the user's presentation
  workstream, per `HANDOFF.md`): `plan.md`, `HANDOFF.md`, `docs/presentation/`,
  `.devcontainer/`, `evaluate_v2.py`. The latter two get committed in later phases
  since the Docker work builds on them.

### Verification (run as-is) — ✅ PASSED

Reran `python src/ball/models/injury_prediction/v2/evaluate_v2.py` (after backing up
`docs/presentation/` to `/tmp/presentation_backup`). The regenerated
`docs/presentation/v2_results.csv` is **byte-identical** to the presentation copy.
Confirmed baseline (temporal 80/20 hold-out, season 2015-10-27 → 2016-04-13,
17,866 player-games, 319 players, 314 injury events):

- **V1 game-level**: ROC-AUC **0.659**, precision 2.1%, recall 57.1%, base rate 1.76%
- **V2 rolling window**: GB beats LR on forward days 5–14, peaking **0.649 (day 9)**;
  LR flat ~0.55. Full table: `docs/presentation/v2_results.csv` — this exact file is
  the Phase 3 verification bar.

### Files added this phase

- `.gitattributes` (rewritten) — LF normalization.
- `CLAUDE.md` — non-negotiables for any future session.
- `DOCKER_PLAN.md` — the build plan (named to avoid case-collision with the untracked
  presentation `plan.md`).
- `work_done.md` — this file.

---

## Phase 1 — Pin the environment (2026-06-10)

- `requirements.txt` frozen to the exact versions installed in the devcontainer —
  i.e. the versions the Phase 0 verification ran against (numpy 2.4.6, pandas 3.0.3,
  scikit-learn 1.9.0, shap 0.52.0, …). Verified with `pip install --dry-run` (no
  conflicts).
- **Added**: `streamlit==1.58.0` (the POC app was never in requirements),
  `supabase==2.31.0` (imported by `connect.py`/`ping.py`, was only installed ad-hoc
  by the devcontainer Dockerfile), `python-dotenv` (replacing the ambiguous `dotenv`
  entry — the `dotenv` PyPI package is a different project that shadows the same
  module name).
- **Dropped** (imported nowhere in the repo — checked all `.py` and `.ipynb`):
  `google`, `selenium`, `polars`. Restore by re-adding a pinned line if ever needed.
- **Kept** although notebook-only: `pandasql` (used by
  `exploration/injury_instance.ipynb`), `SQLAlchemy` (used by v1/extract notebooks).
- New `requirements-dev.txt`: `pytest==9.0.3`, `ruff==0.15.16` (CI/dev only, stays
  out of the Docker image).
- System-level deps: none beyond Python 3.12 — every pin ships a manylinux wheel
  (psycopg2-binary bundles libpq; SQLite is in the stdlib).

---

## Phase 2 — Base Docker image (2026-06-10)

- `Dockerfile`: multi-stage on `python:3.12.11-slim-bookworm` (exact match for the
  devcontainer's Python 3.12.11). Builder stage wheels the pinned requirements;
  runtime installs from wheels only (`--no-index`), copies `src/` + `data/`
  (sample CSVs ship in the image so the pipeline can bootstrap with zero mounts),
  runs as non-root user `ball`, and exposes the two volume mount points:
  `BALL_DB_PATH=/data/BALL.db`, `BALL_ARTIFACTS_DIR=/artifacts`.
  `PYTHONPATH=/app/src` makes `python -m ball.pipeline.*` work in-container.
- `.dockerignore`: excludes git, docs, tests, envs, DBs.
- `pyproject.toml`: minimal setuptools packaging (src layout) so `pip install -e .`
  works locally/CI; also carries ruff + pytest config scoped to the production path.
- ⚠️ **Not built locally — this devcontainer has no Docker CLI.** The image is
  authored here and verified by the CI `docker build` + in-container smoke test
  added in Phase 8. (Flagged in `DOCKER_PLAN.md` as [ADAPTED].)

---

## Phase 3 — Extract the pipeline (2026-06-10) ★ the big one

### What was built — `src/ball/pipeline/`

| Module | Role | CLI |
|---|---|---|
| `config.py` | env-driven paths (`BALL_DB_PATH`, `BALL_ARTIFACTS_DIR`), V2 defaults (X=Y=14, seed 42, 80/20 temporal) | — |
| `bootstrap.py` | sample CSVs → SQLite (`model_input`, `game_dates`, `players`) | `python -m ball.pipeline.bootstrap` |
| `data.py` | SQLite access; reproduces `evaluate_v2.load_data()` exactly (rowid-ordered reads keep CSV row order) | — |
| `targets.py` | per-forward-day binary targets (strictly-after / inclusive-end rule) | — |
| `features.py` | X-day window mean/std/min/max aggregation + dataset assembly | `…features --lookback 14 --horizon 14` |
| `train.py` | temporal split + per-day LogReg & GradientBoosting; saves preprocess/models/meta | `…train --horizon 14 --model both` |
| `evaluate.py` | per-day ROC-AUC on the hold-out + **automatic comparison against the frozen reference** (exits 1 on drift) | `…evaluate` |
| `explain.py` | SHAP beeswarm + mean-abs-SHAP ranking for a chosen day | `…explain --day 7` |
| `reference/v2_results_2015-16.csv` | frozen reference numbers (= the presentation table) | — |

Plus `tests/` (12 tests): target boundary semantics, window aggregation values,
dataset round-trip, and the **temporal-split guard** — train dates must all
precede test dates, and `train.py`'s source may not contain
`train_test_split`/`shuffle(`/`permutation(`.

The math was ported **verbatim** from `evaluate_v2.py` (which is now committed
as the reference implementation); the official V2 notebook's random stratified
split was *not* carried over — temporal split per the plan's non-negotiables.

### Verification — ✅ bit-identical

`bootstrap → features → train → evaluate` on the sample season:

```
max |Δ test_pos_rate|: 9.54e-17   (one ulp in a mean)
max |Δ lr_auc|:        0.00e+00   ← bit-identical, all 14 days
max |Δ gb_auc|:        0.00e+00   ← bit-identical, all 14 days
✅ PASS (tolerance 1e-06)
```

`explain` reproduces the documented SHAP story (top drivers: possessions_max,
distance_max, minutes_max, distance_std, age_mean, usagepercentage_max).

### The one real bug the gate caught

First run: GB bit-identical but **LR off by up to 2.1e-3**. Cause: the dataset
is persisted to CSV between `features` and `train`, and pandas' default fast
float parser is ~1 ulp lossy on read-back. Threshold-based GB is insensitive to
that; LBFGS-optimized LogisticRegression amplifies it into the 3rd decimal of
AUC. Fix: `pd.read_csv(..., float_precision="round_trip")` in
`train.load_dataset`. Lesson recorded here on purpose: **per-day AUC comparison
is sensitive enough to catch a single-ulp serialization bug** — keep the
reference check wired into CI.

### Also in this phase

- `.gitignore`: `artifacts/`, `*.egg-info/`, proper `__pycache__/` pattern.
- `pip install -e .` works (pyproject from Phase 2); `ruff check .` clean.

---

## Phases 4 + 7 — Containerized run, compose + make (2026-06-10)

*(Committed together: the Makefile and compose file are one coherent unit —
splitting them would have meant committing a Makefile referencing services
that don't exist yet.)*

- `docker-compose.yml`: three services off **one shared image** —
  `pipeline` (one-shot chain: bootstrap → features → train → evaluate →
  explain; profile-gated so `docker compose up` doesn't auto-run it),
  `app` (Streamlit on :8501 with a healthcheck), `notebook` (optional Jupyter
  Lab on :8888, repo mounted over /app, profile-gated). Two named volumes:
  `ball-db` → `/data` (SQLite), `ball-artifacts` → `/artifacts` (models,
  dataset, evaluation, SHAP). Retraining never requires an image rebuild.
- `Makefile`: native targets (`make data/features/train/evaluate/explain/
  pipeline/app/test/lint`) and containerized twins (`make docker-*`,
  `make up/down/build/notebook`). Native targets verified here
  (`make evaluate` → ✅ PASS); docker targets validated as YAML + verified in CI.
- `.devcontainer/` (created by the previous session, was untracked) committed:
  it's the dev-side counterpart of the same environment and installs the same
  pinned `requirements.txt`.
- `docs/docker.md`: the "Running in Docker" page — quickstart, service/volume
  tables, where the data comes from, native fallback, reproducibility contract.

---

## Phase 5 — Data acquisition path (2026-06-10)

- **Fast path (no credentials, no network)**: the repo/image ships one sample
  season — `model_input_file.csv` (the materialized output of
  `proof_of_concept_use_case/model_input_base.sql` against the original DB,
  17,866 player-games incl. `is_injured`) + `game_dates.csv` + `players.csv`.
  `python -m ball.pipeline.bootstrap` loads them into SQLite. This is what CI
  and demos use.
- **Full path (documented, not containerized)**: Supabase (Postgres) holds the
  full relational data; `.env` carries credentials (`.env.example` extended
  with the pipeline path vars too). Rebuilding from sources uses the existing
  ETL in `src/ball/scripts/` (nba_api game stats/tracking/anthro pipelines,
  `nba_injury_report_ETL/` for 2021+ injury reports). Deliberately left
  outside the reproducible container path — it needs network + credentials.
  Documented in `docs/docker.md` ("Where the data comes from").
- `README.md` updated: Docker + native quickstarts, `pipeline/`+`app/`+`tests/`
  rows in the repo-structure table, and the data-sources paragraph now states
  the Supabase reality (the old text implied everything was still in SQLite).

---

## Phase 6 — Dashboard (2026-06-10)

- `src/ball/app/app.py` — the Streamlit POC rebuilt on top of `ball.pipeline`
  (the old `models/.../streamlit_app.py` had a broken import path and read a
  DB that no longer exists; it stays in place as reference per the
  leave-models-alone rule). The app now renders the repo's own "planned
  additions": the **day-by-day risk curve** (signature output), the **workload
  timeline with injury markers**, and the **SHAP top-drivers** chart (reads the
  explain step's output when present). Model family selectable
  (GB winner / LR baseline); fuzzy player search via thefuzz; honest caption
  that scores are relative risk, not calibrated probabilities.
- Artifacts/DB come from `$BALL_ARTIFACTS_DIR`/`$BALL_DB_PATH` — the same
  volumes the pipeline writes, so the compose `app` service reads what the
  trainer wrote with no rebuild.
- **Verified headlessly** with Streamlit's `AppTest`: renders, fuzzy-matches
  "LeBron James", predicts off his last 14 days (6 games, window ending
  2016-04-11), renders the probability table — no exceptions. That check is
  committed as `tests/test_app.py` (auto-skips when artifacts are absent;
  13/13 tests green locally).

---

## Phase 8 — CI + reproducibility (2026-06-10)

New `.github/workflows/ci.yaml` (the existing `main.yaml` Supabase keep-alive
is untouched), two jobs:

1. **pipeline** (native, Python 3.12): ruff → unit tests (temporal-split guard
   included; app test auto-skips pre-artifacts) → **full pipeline on the sample
   season** — the evaluate step *is* the regression test, exiting non-zero if
   any per-day ROC-AUC drifts from the frozen reference → artifact assertions →
   headless AppTest against the freshly trained artifacts.
2. **docker**: `docker build` → in-container bootstrap→features→train→evaluate
   (horizon 2 for speed; days 1–2 still compared against the reference) →
   `docker compose up app` and poll its healthcheck endpoint until healthy.

This is where the Docker assets get their real verification, since this
devcontainer has no Docker CLI. **First run happens when the `dockerize`
branch is pushed.**

---

## Status & how to continue (handoff)

### Done — all phases 0–8, each as a commit on `dockerize`

```
12eca55  chore: normalize line endings to LF repo-wide
afb8d88  docs: dockerization plan, CLAUDE.md guardrails, work log (Phase 0)
e4c561c  build: pin dependencies to verified versions (Phase 1)
e856ff9  build: multi-stage base Docker image + packaging (Phase 2)
5011af3  feat: extract V2 pipeline into ball.pipeline modules (Phase 3)
e4ed4a0  feat: compose services, Makefile one-liners, devcontainer (Phases 4+7)
936ee99  docs: data acquisition path + README quickstarts (Phase 5)
a966524  feat: Streamlit risk-curve dashboard on ball.pipeline (Phase 6)
4a74bc2  ci: lint, pipeline regression smoke, docker build + app health (Phase 8)
```

**Closing verification (2026-06-10):** deleted `data/BALL.db` + `artifacts/`,
ran `make pipeline` from scratch → bit-identical to the reference again
(max |ΔAUC| = 0.0 both families), `pytest` 13/13, `ruff` clean.

### Not done / waiting on you

1. **Push and watch the first CI run** — `git push -u origin dockerize`.
   The docker job is where the image build gets its first real verification
   (no Docker CLI in this devcontainer). If it fails, the likely suspects are
   the base tag (`python:3.12.11-slim-bookworm`) or compose-on-runner quirks —
   both easy fixes.
2. **Merge to `main`** via PR when CI is green.
3. **Still untracked on purpose** (your presentation workstream, per
   `HANDOFF.md`): `plan.md`, `HANDOFF.md`, `docs/presentation/`. Decide their
   fate after Friday.
4. Roadmap items deliberately out of scope: Supabase-backed full-data pipeline
   runs, nested temporal CV, multi-season data (all in README "Next Steps").

### Cheat sheet

```bash
make pipeline          # sample CSVs → SQLite → dataset → 14×2 models → eval (verifies) → SHAP
make app               # dashboard, natively
make docker-pipeline   # same chain in a container (volumes: ball-db, ball-artifacts)
make up                # dashboard at http://localhost:8501
make test && make lint
```
