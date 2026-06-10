# CLAUDE.md — working rules for this repo

BALL predicts NBA player injury risk: given the previous X days (default 14) of game
data, Y models (default 14) each predict the probability of injury within the next
1…Y days, producing a day-by-day risk curve.

## Non-negotiables (containerization work)

- **This is a containerization task. Preserve V2's science exactly**: multi-target
  per-forward-day models, X/Y windows, mean/std/min/max aggregation, ROC-AUC as the
  primary metric. Do not collapse to a single classifier.
- **Splits stay temporal — never random shuffle.** Train on the earliest 80% of
  observation dates, test on the latest 20%. Move toward nested temporal CV, don't
  regress from it. (`tests/test_temporal_split.py` enforces this.)
- **Production path = extracted modules in `src/ball/pipeline/`.** Notebooks in
  `src/ball/exploration/` and `src/ball/models/` stay as research references — leave
  them alone.
- **SQLite is the local store.** The pipeline reads a file-based SQLite DB
  (`data/BALL.db`, built by `python -m ball.pipeline.bootstrap` from the sample CSVs).
  Mount it as a volume in Docker; do not add a database service for it.
- **Verify every change by running it.** The reference numbers are
  `docs/presentation/v2_results.csv` (per-forward-day ROC-AUC, temporal hold-out);
  pipeline changes must reproduce them. Commit at the end of each phase.

## Data reality (read before assuming)

- The **remote/full** data store is **Supabase (Postgres)** — `connect.py` / `ping.py`
  and the daily keep-alive workflow talk to it. The legacy local `BALL.db` was removed
  from the repo.
- The **reproducible local path** runs from CSVs shipped in the repo:
  `src/ball/models/injury_prediction/v2/model_input_file.csv` (game-level features +
  `is_injured`, one season 2015-16) and `data/1-nba_api/game_dates.csv`.
  `ball.pipeline.bootstrap` loads these into SQLite so the pipeline has a DB to read.
- Injury labels in the sample data come from the `is_injured` column; there is no
  standalone injuries table in the sample CSVs.

## Where things live

- `src/ball/pipeline/` — extracted production pipeline (features, targets, train,
  evaluate, explain, bootstrap) with `python -m` CLIs.
- `src/ball/app/` — Streamlit risk-curve dashboard.
- `src/ball/models/injury_prediction/` — original research notebooks (reference only).
  `v2/evaluate_v2.py` is the verified reference implementation the pipeline was
  extracted from.
- `docs/presentation/` — presentation assets for the 2026-06-12 talk. **Do not modify
  or delete**; regenerating via `evaluate_v2.py` is OK (it reproduces them).
- `DOCKER_PLAN.md` — the phased containerization plan. `work_done.md` — the running
  log of what was done per phase.

## Commands

```bash
make help        # all targets
make data        # bootstrap SQLite from sample CSVs
make features    # build windowed dataset
make train       # train Y per-day models
make evaluate    # per-horizon ROC-AUC vs reference
make app         # Streamlit dashboard
pytest tests/    # unit tests incl. the temporal-split guard
```

Inside Docker the same targets run via `docker compose run pipeline ...`; see
`DOCKER_PLAN.md` and `docs/docker.md`.
