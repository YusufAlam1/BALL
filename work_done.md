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

*(Later phases appended below as they complete.)*
