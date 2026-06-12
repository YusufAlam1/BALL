# BALL — Presentation Plan (Friday 2026-06-12)

> **Resuming work?** Read **`HANDOFF.md`** (repo root) first — it has the state of play, git status, and how to restart.

**Goal:** Be ready to present BALL to your research supervisor and professor on **Friday**.
**Format:** Slides / narrative (no live demo required).
**Data backend:** Project has migrated to **Supabase/Postgres**. The legacy local `BALL.db` (SQLite) is gone from the repo.

> The story is already strong — `README.md` carries the full narrative (problem, formulation, methodology, impact). The gap is **evidence**: the V2 results are described qualitatively, there are **no figures**, and there are **no concrete per-day numbers**. This plan closes that gap with the least risk.

---

## TL;DR — the critical path

For a slides-only talk, you need three things by Friday, in priority order:

1. **Concrete V2 results** — real per-forward-day ROC-AUC numbers for Logistic Regression vs. Gradient Boosting.
2. **4 figures** that make the narrative visual and defensible.
3. **A tight slide outline** mapping the README story to ~12 slides.

Everything else (Streamlit demo, import bugs, DB porting) is **out of scope for Friday** — see "Explicitly deferred" at the bottom.

---

## P0 — Results & figures ✅ DONE (2026-06-08)

**Status: complete and reproducible.** Built `src/ball/models/injury_prediction/v2/evaluate_v2.py`,
which runs entirely from local CSVs (joined `model_input_file.csv` + `data/1-nba_api/game_dates.csv` —
the dates the old SQLite path provided). **No database needed.**

> Note: the saved `artifacts/*.joblib` models would not unpickle (sklearn 1.9 vs the version they were
> trained on — `ModuleNotFoundError: _loss`). So the script **retrains fresh from the CSV**, which is
> more honest and fully reproducible anyway.

### Reproduced numbers (temporal hold-out, single season 2015-16)
- **V1 game-level:** ROC-AUC **0.659**, precision **2.1%**, recall **57%**; base rate **1.76%** (314/17,866).
  → backs the "naive per-game prediction fails" pivot.
- **V2 rolling window:** Gradient Boosting **beats** Logistic Regression across days **5–14**, peaking at
  **AUC ≈ 0.65 (days 6–9)**; LR flat at ~0.55. Full per-day table in `docs/presentation/v2_results.csv`.

### Figures produced → `docs/presentation/figures/`
- [x] `fig1_auc_vs_forward_day.png` — LR vs GB ROC-AUC across the 14-day horizon (**headline**)
- [x] `fig2_feature_importance.png` — GB top features (age, peak minutes, pace, distance volatility…)
- [x] `fig3_player_probability_curve.png` — signature day-by-day risk curve for a sample player
- [x] `fig4_positive_rate_by_horizon.png` — positive rate climbs 0.25%→4.5% (the imbalance story)

### Honest caveats to carry into slides
- Single season, 314 injury events → small/noisy positive class; numbers should rise with multi-season data.
- Probability curve values are **relative risk scores** (class-balanced training), not calibrated probabilities.

### Follow-ups ✅ DONE (2026-06-08)
- [x] True **SHAP** beeswarm on the GB 7-day model → `docs/presentation/figures/fig2b_shap_beeswarm.png`
      (top drivers: peak possessions/distance/minutes, distance volatility, age, usage %).
- [x] Player **workload timeline with actual injury markers** → `docs/presentation/figures/fig5_workload_timeline.png`.
- [x] Slide deck with **speaker notes** → `docs/presentation/outline.md` (now 15 slides + Q&A).

---

## P1 — Narrative & slide outline

The content already exists in `README.md`; this is distillation, not writing from scratch.

- [x] Draft a **~14-slide outline** → see `docs/presentation/outline.md` (real numbers + which figure per slide + Q&A prep). Confirm timing with whatever slot you have.
- [ ] Make sure the **iteration story** lands — Phase 1 (recovery regression) → V1 (per-game classification, why it failed: 1.7% base rate, ~4% precision) → V2 (rolling window + per-day curve). The "we tried X, it failed for reason Y, so we did Z" arc is what research reviewers reward.
- [ ] Have a one-liner ready for **"why ROC-AUC and not accuracy/precision"** (rare-event class imbalance; threshold-independent discriminative ability) — likely question from the professor.
- [ ] Prepare the **limitations slide honestly** (class imbalance, tracking-data coverage gaps, no out-of-time validation yet, severity not stratified). Reviewers trust a talk more when limitations are stated plainly.

### Suggested slide outline
1. Title + one-sentence pitch (player-specific daily injury-risk curve)
2. The problem & cost (load management is guesswork; injury cost)
3. Problem formulation (X-day lookback → per-day Y-forward probability)
4. Data sources (movement/load, performance, anthropometrics, injury history) + Supabase schema
5. Iteration 1 — recovery-duration regression (result + lesson)
6. Iteration 2 — V1 per-game classification (why it failed)
7. V2 methodology — feature aggregation + per-day targets + 2 model families
8. **Figure 1** — ROC-AUC vs forward day (results)
9. **Figure 3** — sample player probability curve (signature output)
10. **Figure 2 / 4** — feature importance &/or workload-vs-injury timeline
11. Limitations (honest)
12. Next steps / roadmap (pull from README "Next Steps")

---

## P2 — Repo presentability (only if time allows)

Reviewers may glance at the repo. Low-effort polish:
- [ ] Add `streamlit` and `supabase` to `requirements.txt` (currently installed ad-hoc; makes the repo reproducible).
- [ ] Commit the new untracked `.devcontainer/` (or `.gitignore` it) so `git status` is clean for any screen-share.
- [ ] One sentence in `README.md` noting the data backend is now Supabase/Postgres (the README still implies SQLite `BALL.db`).

---

## Explicitly deferred (NOT for Friday)

These are real issues but irrelevant to a slides-only talk — listed so they aren't forgotten:
- **Streamlit demo is broken.** `streamlit_app.py` imports `ball.models.injury_prediction.v2.injury_prediction_v2`, but that module lives in `proof_of_concept_use_case/`, not `v2/`. App crashes on launch.
- **Model/POC code still uses SQLite.** `injury_prediction_v2.py` reads `db/BALL.db` (which no longer exists). Needs porting to Supabase to run live again.
- Out-of-time / held-out-season validation, nested temporal CV, injury-type stratification, injury-report status features — all in the README roadmap, all post-Friday.

---

## Day-by-day (today is Mon 2026-06-08)

- **Mon–Tue:** P0 — pin V2 numbers, build Figures 1 & 3. (Highest risk; do first.)
- **Wed:** P0 — Figures 2 & 4; save all to `docs/presentation/figures/`.
- **Thu:** P1 — assemble slides, rehearse the iteration arc + likely Q&A.
- **Fri AM:** buffer — P2 polish only if everything above is done.
