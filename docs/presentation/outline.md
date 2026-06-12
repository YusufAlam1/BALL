# BALL — Presentation Outline + Speaker Notes (Friday 2026-06-12)

Slide-by-slide deck with **real, reproduced numbers**, the figure for each slide, and **speaker notes**
(roughly what to say out loud). All numbers are reproducible from
`src/ball/models/injury_prediction/v2/evaluate_v2.py` (local CSVs only, no DB). Figures live in
`figures/` next to this file; the per-day results table is `v2_results.csv`. See `HOW_TO_RUN.md` to regenerate.

> **Data scope (state this up front — it's the honest caveat):** results are from a **single
> season, 2015-10-27 → 2016-04-13**: 17,866 player-game rows, 319 players, **314 injury events**.
> Evaluation uses a **temporal hold-out** (train on earliest 80% of dates, test on latest 20%),
> stricter than a random split and free of look-ahead leakage.

Target length: ~15 slides, ~12–15 min. Speaker notes are written to be paraphrased, not read verbatim.

---

## Slide 1 — Title
- **BALL: Player-specific daily injury-risk curves for the NBA**
- *"Not 'is this player at risk?' but 'how does their risk evolve over the next two weeks?'"*
- Your name · supervisor · lab/course · date.

**Speaker notes:** "Injuries are the most expensive thing in pro basketball that teams can actually
influence, yet load-management decisions are still mostly intuition. BALL is my attempt to put a number
on it — a per-player, per-day injury-risk curve. I'll walk through the problem, three modeling iterations,
what works, and where it goes next. I'll be upfront that this is one season of data — the contribution is
the framework and the pipeline as much as the headline number."

## Slide 2 — The problem & why it matters
- Injuries are the largest *controllable* cost in pro basketball; ~15–20 player-games lost per team per season.
- Today's load management = back-to-back rules, subjective feel, blanket policies.
- Goal: a quantified, player-specific, per-day risk score that turns reactive into preventive.

**Speaker notes:** "A single season-ending injury to a star can cost a franchise tens of millions in sunk
salary, plus the knock-on competitive cost. But the way teams decide who rests is crude — mostly schedule
density and how a player says they feel. None of that is personalized to a player's actual recent workload
or injury history. That gap is the opportunity."

## Slide 3 — Problem formulation
- Using the previous **X = 14 days** of game data, predict **P(injury within d days)** for d = 1…14.
- **One model per forward day** → a probability *curve*, not a single yes/no.
- Each target is binary: *was the player injured within d days of this observation point?*

**Speaker notes:** "Here's the core framing. I take a rolling 14-day window of a player's games and ask, for
each of the next 14 days, what's the probability they get injured within that many days. That's 14 separate
binary targets, one model each. The output isn't a flag — it's a trajectory, which is what a coach or medical
staffer actually needs to schedule rest."

## Slide 4 — Data
- Four families: **movement/load** (speed, distance), **performance** (minutes, usage, pace, possessions),
  **anthropometrics** (height, weight, wingspan, body-fat %…), **injury history**.
- Unified relational schema, now on **Supabase/Postgres**. *(Show the ER diagram from `docs/db_schema.md`.)*

**Speaker notes:** "The data spans four dimensions of risk. Workload is the most direct proxy for exposure;
performance metrics capture intensity and role; anthropometrics are the static physical profile from the
draft combine; and injury history, since the best predictor of a future injury is a past one. It all lives in
a relational schema — we recently migrated from a local SQLite database to Supabase/Postgres."

## Slide 5 — Iteration 1: recovery-duration regression (Phase 1)
- Random Forest predicting total days out: **MAE 23.1 d, RMSE 56.6 d, R² 0.598**.
- Lesson: explains ~60% of variance, but the RMSE≫MAE gap means it blows up on severe injuries; too few features.

**Speaker notes:** "First attempt answered a different question — given an injury, how long is the player out?
A random forest got R² around 0.6, decent for a first pass. But the big gap between RMSE and MAE tells you it's
badly wrong on the severe, season-ending cases — exactly the ones that matter most. And it only fires after an
injury already happened. So I pivoted to prediction."

## Slide 6 — Iteration 2: per-game classification (V1) — and why it failed
- **Reproduced: ROC-AUC 0.659, precision 2.1%, recall 57%** (threshold 0.5).
- Base rate is only **1.76%** (314 injuries in 17,866 games) → a per-game flag is wrong ~98% of the time.
- **The problem wasn't the model — it was the formulation.** This motivates rolling windows.

**Speaker notes:** "Next I tried predicting injury per individual game. The model can rank games — AUC about
0.66 — but it's operationally useless: when it flags a game, it's right ~2% of the time, because injuries happen
in under 2% of games. A single game just doesn't carry enough signal. That failure is the whole reason for the
next iteration — aggregate over time instead of betting on one game."

## Slide 7 — V2 methodology: rolling window
- For each observation, aggregate the prior 14 days of games into **mean / std / min / max** of every feature
  → a **56-dimensional** fixed-width vector.
- Build 14 forward targets (injured within 1, 2, … 14 days).
- Train **Logistic Regression** (interpretable baseline) and **Gradient Boosting** (non-linear) per day.
- Aggregation smooths single-game noise; widening windows lift the positive rate.

**Speaker notes:** "V2 fixes the formulation. Instead of one game, I summarize the last 14 days — mean, spread,
min, and max of every metric — into a fixed feature vector. That smooths out single-game noise. Then I train two
model families per forward day: logistic regression as an interpretable baseline, gradient boosting for
non-linear interactions."

## Slide 8 — **Figure 4** + the imbalance story
- `fig4_positive_rate_by_horizon.png`: positive-class rate climbs **0.25% (day 1) → 4.5% (day 14)**.
- Why short horizons are hard, and why we use **ROC-AUC** (threshold-independent) rather than accuracy.

**Speaker notes:** "This chart explains a metric choice. The wider the forward window, the more injury events
fall inside it — from a quarter of a percent at day 1 up to four-and-a-half percent at day 14. The positive class
is always rare, so accuracy is meaningless and the right threshold depends on a team's risk tolerance. That's why
I report ROC-AUC, which measures ranking ability independent of any threshold."

## Slide 9 — **Figure 1**: headline result
- `fig1_auc_vs_forward_day.png`: ROC-AUC vs forward day, LR vs GB.
- **Gradient Boosting beats Logistic Regression across days 5–14**, peaking at **AUC ≈ 0.65 (days 6–9)**.
- LR flat at ~0.55; days 1–2 noisy (too few positives). *Modest but real, consistent across the mid-horizon.*

**Speaker notes:** "Here's the main result. Gradient boosting clearly pulls ahead of logistic regression from
about day 5 on, peaking near 0.65 AUC in the 6-to-9-day range. The first couple of days are noisy because there
are almost no positive events to learn from. I want to be honest: 0.65 is modest. But it's a real, consistent
signal on a hard, rare-event problem with one season of data — and the gradient-boosting-over-baseline gap is
directional, not random."

## Slide 10 — **Figure 2b**: what drives risk (SHAP)
- `fig2b_shap_beeswarm.png` (GB, 7-day target). *(Backup: `fig2_feature_importance.png` bar chart.)*
- Top drivers: **peak possessions, peak distance, peak minutes, distance volatility (std), age, peak usage %**
  — overwhelmingly workload, plus age/physical profile.
- Consistent with sports-medicine literature (workload spikes + age/body composition).

**Speaker notes:** "To check the model is learning something sensible, I ran SHAP on the gradient-boosting model.
The strongest drivers are workload peaks — most possessions, most distance, most minutes in the window — plus how
volatile the distance was, and the player's age. In other words, accumulated and spiky workload plus the physical
profile. That lines up with what the sports-science literature says actually causes injuries, which gives me
confidence the model isn't just fitting noise."

## Slide 11 — Worked example: one player's season (**Figure 5**)
- `fig5_workload_timeline.png`: a real player's game-by-game minutes & distance with **injury events marked**.
- Purpose: show the raw signal the model consumes — a dense per-game workload series, with injury timing overlaid.

**Speaker notes:** "Before the model's output, here's the raw input for one real player across the whole season —
minutes and distance per game, with red lines for actual injury events. For this player the injuries happened
early, and you can see workload is otherwise fairly stable. The point of the slide isn't a dramatic spike; it's
to show the granularity of the per-game series that the rolling-window features summarize into risk."

## Slide 12 — **Figure 3**: the signature output
- `fig3_player_probability_curve.png`: day-by-day risk curve for that player from their last 14 days of load.
- The differentiator: risk **shape over time** → concrete decisions (rest tonight vs. reduce minutes over weeks).
- *Caveat:* class-balanced models → values are **relative risk scores**, not calibrated probabilities (future work).

**Speaker notes:** "And here's what BALL produces for that player — a day-by-day risk curve from their recent
load. This is the differentiator versus a binary classifier: it tells you not just whether risk is elevated but
*when* it peaks, which maps directly onto a rest-tonight versus manage-minutes-over-two-weeks decision. One
honest caveat — because I train with balanced class weights, treat these as relative risk scores rather than
calibrated probabilities; calibration is on the roadmap."

## Slide 13 — Limitations (say these plainly)
- **Single season**; 314 injury events → small, noisy positive class.
- Tracking data (speed/distance) and combine anthropometrics are incompletely covered.
- No multi-season out-of-time validation yet; injuries not stratified by severity/type.
- Probabilities uncalibrated.

**Speaker notes:** "I'll be direct about the limits. This is one season and a few hundred injury events, so the
positive class is small and noisy. Tracking and combine data have coverage gaps. I haven't yet validated on a
fully held-out future season, and right now a sprained ankle and a torn ACL count the same. These are exactly
the things the roadmap targets."

## Slide 14 — Next steps / roadmap
- Multi-season data + true out-of-time validation; nested temporal cross-validation.
- Injury-type / body-region stratified models.
- Game-context features (back-to-backs, travel, home/away) + play-by-play intensity.
- Integrate official NBA injury-report status trajectory (2021+).
- Probability calibration; ensemble of likelihood × expected-recovery.

**Speaker notes:** "The path forward is concrete: more seasons and genuine out-of-time validation to get an
honest performance estimate; separate models per injury type; richer context features like back-to-backs and
travel; the official injury-report status trajectory; and calibration so the numbers are true probabilities. I'd
expect the headline metric to rise meaningfully with multi-season data."

## Slide 15 — Summary
- Reformulating injury prediction as a **per-day rolling-window curve** turns an unusable per-game classifier
  (2% precision) into a usable risk-trajectory tool (**AUC ~0.65 mid-horizon**), with a clear path to stronger
  results via more data and validation.

**Speaker notes:** "To wrap up: the key move was changing the question — from 'will this game cause an injury,'
which is hopeless at 2% precision, to 'how does risk build over the next two weeks,' which gives a usable curve
at around 0.65 AUC. The framework, the pipeline, and the reproducible evaluation are in place; scaling the data
is what unlocks the next level. Happy to take questions."

---

## Anticipated Q&A (prep these)
- **"Why ROC-AUC and not accuracy/precision?"** — Rare-event imbalance; AUC measures discrimination independent
  of threshold, and the right threshold depends on the team's risk tolerance.
- **"Is 0.65 good?"** — Honest: modest, single-season, small positive class. The contribution is the *formulation*
  + pipeline; GB > LR is consistent/directional; expect gains with multi-season data.
- **"Isn't there leakage?"** — No: temporal hold-out (train past, test future); lookback windows only use games
  on/before the observation date.
- **"How is `is_injured` defined?"** — Injury event tied to a game date; forward target = any injury event within
  d days after the observation.
- **"Why does the probability curve sit near 0.3–0.5?"** — Class-balanced training inflates absolute scores; treat
  as relative risk. Calibration is on the roadmap.
- **"Why gradient boosting over deep learning / survival models?"** — Sample size (314 events) favors lower-variance
  models; GB also gives SHAP interpretability. Survival analysis is a natural future direction.

## Reproducing the numbers/figures
```bash
python src/ball/models/injury_prediction/v2/evaluate_v2.py
# prints V1 + V2 tables; writes docs/presentation/figures/*.png and docs/presentation/v2_results.csv
```
Full step-by-step (env + troubleshooting) is in `HOW_TO_RUN.md`.
