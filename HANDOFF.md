# HANDOFF — start here when you come back

_Last updated: 2026-06-08. Goal: be ready to present BALL on **Friday 2026-06-12** (slides/narrative, no live demo)._

This is the entry point. Read this first, then jump to the linked docs.

---

## TL;DR — where things stand

The presentation is **essentially ready to assemble into slides.** Everything you need was produced
this session and lives in **`docs/presentation/`**, all reproducible from one script with no database.

- ✅ Real, reproducible model results (V1 baseline + V2 per-day ROC-AUC)
- ✅ Six slide-ready figures
- ✅ A 15-slide outline **with speaker notes** and Q&A prep
- ✅ A run guide to regenerate everything
- ⬜ Not yet done: actually build the slide deck file (PowerPoint/Google Slides) from the outline
- ⬜ Not committed to git (see "Git state" below)

---

## The handoff doc set (read in this order)

1. **`HANDOFF.md`** (this file) — state of play + how to resume.
2. **`plan.md`** (repo root) — the Friday checklist; what's done / deferred, day-by-day.
3. **`docs/presentation/outline.md`** — the deck: 15 slides, speaker notes, Q&A, figure-per-slide.
4. **`docs/presentation/HOW_TO_RUN.md`** — how to regenerate every number and figure.

---

## What was produced this session

| File | What it is |
|------|------------|
| `src/ball/models/injury_prediction/v2/evaluate_v2.py` | The evaluation script — single source of truth for all numbers/figures. Retrains from CSV (no DB). |
| `docs/presentation/outline.md` | 15-slide outline + speaker notes + Q&A |
| `docs/presentation/HOW_TO_RUN.md` | Setup + run + troubleshooting |
| `docs/presentation/figures/fig1..fig5*.png` | The six figures |
| `docs/presentation/v2_results.csv` | Per-forward-day ROC-AUC table (LR vs GB) |
| `plan.md` | Friday-focused checklist |

## Key results to remember (so you don't re-derive them)

- **Data scope:** single season 2015-10-27 → 2016-04-13; 17,866 player-games, 319 players, **314 injury events**.
- **Evaluation:** temporal hold-out (train earliest 80% of dates, test latest 20%) — no look-ahead leakage.
- **V1 (per-game classification, the "naive" baseline):** ROC-AUC **0.659**, precision **2.1%**, recall **57%**;
  base rate **1.76%**. → justifies the pivot to rolling windows.
- **V2 (rolling window):** Gradient Boosting **beats** Logistic Regression across forward days **5–14**,
  peaking at **AUC ≈ 0.65 (days 6–9)**; LR flat ~0.55.
- **SHAP top drivers (7-day target):** peak possessions / distance / minutes, distance volatility, age, usage %.

## Honest caveats (carry these into the talk — don't get caught in Q&A)

- One season, small/noisy positive class → numbers should rise with multi-season data; sell the *formulation + pipeline*.
- Probability-curve values are **relative risk scores** (class-balanced training), not calibrated probabilities.
- The workload-timeline figure (fig5) is the weakest — its player's injuries cluster early; framed modestly in the outline.

---

## How to resume the work

**To regenerate everything (after a fresh clone / new machine):**
```bash
cd /workspaces/BALL
pip install -r requirements.txt
python src/ball/models/injury_prediction/v2/evaluate_v2.py
```
This prints the V1 + V2 tables and writes all figures + `v2_results.csv` into `docs/presentation/`.
Full details + troubleshooting: `docs/presentation/HOW_TO_RUN.md`.

**To build the deck:** open `docs/presentation/outline.md`, create one slide per section, drop in the
matching figure from `docs/presentation/figures/` (the outline names which figure goes on which slide),
and use the speaker-notes paragraphs as your notes.

---

## Open next actions (in priority order)

1. **Build the actual slide file** from `outline.md` (the only thing between you and "presentation-ready").
2. *(Optional)* Stronger fig5: pick a player whose injuries are spread across the season with a visible
   workload run-up. Offered but not done — ask Claude to do this, it's a small tweak to `evaluate_v2.py`.
3. *(Optional, P2 in plan.md)* Add `streamlit` + `supabase` to `requirements.txt`; decide whether to
   commit or `.gitignore` `.devcontainer/`.
4. *(Deferred, post-Friday)* Fix the broken Streamlit import and port the model code from SQLite to
   Supabase. See "Explicitly deferred" in `plan.md`.

---

## Git state ⚠️ (read before committing)

- Branch: **`main`**, last commit `0a35c40`. **Nothing from this session is committed.**
- **My session files are untracked:** `plan.md`, `HANDOFF.md`, `docs/presentation/**`,
  `src/ball/models/injury_prediction/v2/evaluate_v2.py`.
- ⚠️ **The working tree also has ~47 pre-existing modified files and other untracked items
  (`.devcontainer/`, etc.) that are NOT from this session.** Don't blanket `git add .`.
- Suggested scoped commit when ready (on a branch, not straight to `main`):
  ```bash
  git checkout -b presentation-prep
  git add plan.md HANDOFF.md docs/presentation src/ball/models/injury_prediction/v2/evaluate_v2.py
  git commit  # describe the presentation eval + figures + outline
  ```
- Nothing has been pushed. Ask before committing/pushing — confirm the scope first.

## Environment note (not in the repo)

The Claude Code **status line** was configured this session to mirror your devcontainer shell prompt.
That lives in `~/.claude/` (`settings.json` + `statusline-command.sh`), **outside this repo** — it
travels with your machine, not the project. To change it, ask Claude to use the `statusline-setup` agent.
