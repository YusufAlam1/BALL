# BALL

Probabilistic injury risk prediction for NBA players using historical game data, player biometrics, and injury records

---

## Project Overview

Player injuries remain the single largest source of uncontrollable cost in professional basketball. A single season-ending injury to a max-contract player can cost a franchise upwards of $30 million in sunk salary, and the downstream effects on team performance compound well beyond the balance sheet. Despite this, load management decisions across the league are still driven largely by intuition, rigid rest schedules, and how a player reports feeling on a given day.

BALL's research project aims to replace that guesswork with a quantifiable, player-specific injury risk score. The core model takes a configurable window of recent game data for a player and outputs a day-by-day probability curve estimating how likely that player is to sustain an injury over each of the following days.

As a concrete example: given the previous 14 days of game data for a player: minutes played, speed, distance covered, usage rate, and other workload and performance indicators, the model produces an injury probability estimate for each of the next 14 days. Rather than a single binary "at risk / not at risk" flag, the output is a temporal curve that reveals how risk accumulates and where it peaks.

---

## Problem Formulation

The prediction task is formulated as follows:

> Using the previous **X days** of game-level data for a player, predict the probability of injury within each of the next **1, 2, 3, ... Y days**

In the default configuration, X = 14 and Y = 14, though both parameters are adjustable. This produces 14 separate prediction targets per observation - one for each forward day. Each target is binary: *was the player injured within d days of the observation point?*

A separate model is trained for each forward day. This multi-target architecture allows the resulting probability curve to reflect how injury risk shifts across the horizon, rather than collapsing the question into a single yes-or-no answer

This formulation emerged after iterating through earlier approaches:

- **Days-out regression**: predicting total recovery duration given an injury event. Limited by sparse features and poor performance on severe injuries
- **Game-level binary classification**: predicting whether an injury occurs during a specific game. Rendered impractical by extreme class imbalance (~1.7% positive rate), leading to precision below 4%

The rolling-window approach solves both problems. Temporal aggregation smooths the noise inherent in single-game data, and the per-day target structure avoids the all-or-nothing fragility of a single binary classifier

---

## Data Sources

The model draws on four categories of variables, each capturing a different dimension of injury risk. All data is consolidated into a SQLite database with relational structure across players, games, injuries, and tracking data

### Movement and Load

Physical workload is the most direct proxy for injury exposure

| Variable | Description |
|----------|-------------|
| **Speed** | Player velocity derived from tracking data, measured per game. Captures the intensity of movement beyond what box-score statistics reflect |
| **Distance** | Total distance covered during a game. Combined with minutes played, this distinguishes between players who are on the court and players who are active on the court |

### Performance

Playing intensity, minute burden, and role within a team's offensive and defensive system

| Variable | Description |
|----------|-------------|
| **Minutes** | Total minutes played. The single most straightforward measure of exposure |
| **Field goal attempts/makes** | Volume and efficiency of scoring. Higher-usage players tend to absorb more physical contact |
| **Rebounds** | Offensive and defensive. Involves repeated jumping, landing, and physical contention - mechanically demanding actions |
| **Assists, turnovers** | Indicators of ball-handling burden and decision-making load |
| **Usage percentage** | Proportion of team possessions a player uses while on the floor. High-usage players face compounding fatigue |
| **Pace, possessions** | Team-level tempo metrics that contextualize individual workload within game speed |

### Anthropometrics

Baseline physical profiles captured at the NBA Draft Combine. These are static per player but influence the mechanical stresses a body endures

| Variable | Description |
|----------|-------------|
| **Height, weight** | Fundamental body dimensions. Heavier players absorb more force on deceleration and landing |
| **Wingspan, standing reach** | Limb proportions that affect movement mechanics and contact surfaces |
| **Body fat percentage** | Body composition indicator. Relevant to both load-bearing capacity and conditioning level |
| **Hand dimensions** | Length and width. Included as available anthropometric data from the Combine; less directly tied to injury risk but part of the full physical profile |

### Injury History

The strongest predictors of future injury are past injuries

| Variable | Description |
|----------|-------------|
| **Prior injury count** | Cumulative number of injury events in a player's career up to the observation point. Players with more prior injuries are statistically more likely to sustain subsequent ones |
| **Days since last injury** | Recency of the most recent injury. Short intervals between injuries suggest incomplete recovery or structural vulnerability |
| **Body region** | Affected area: knee, ankle, shoulder, back, and others. Certain regions carry higher reinjury rates |
| **Diagnosis** | Type of injury: sprain, strain, fracture, tear, and others. Severity and recurrence patterns vary significantly by diagnosis |
| **Return status** | Day-to-day, out, game-time decision. Captures the clinical assessment of injury severity at the time of reporting |

### Sources

Data is drawn from NBA official statistics, player tracking systems, Draft Combine measurements, and official injury reports (available from 2021 onward). The variables above are derived from these sources and stored in a unified relational schema

---

## Methodology

### Current Approach (V2)

The modeling workflow proceeds in four stages:

**1. Feature Aggregation.** For a given lookback window of X days, game-level metrics are aggregated into summary statistics: mean, standard deviation, minimum, and maximum. This transforms a variable-length sequence of game records into a fixed-width feature vector. The aggregation captures both central tendency (how has the player been performing on average) and variation (how volatile has their workload been)

**2. Target Construction.** For each forward day *d* (from 1 through Y), a binary target is constructed: did the player sustain an injury within *d* days of the observation point? This yields Y separate classification targets per training example, each with a progressively wider positive window

**3. Model Training.** One model is trained per forward day, two model families are evaluated:
- *Logistic Regression* serves as the interpretable baseline. Coefficient magnitudes directly indicate feature importance, and predictions are well-calibrated probabilities
- *Gradient Boosting* provides higher capacity for capturing non-linear interactions between features. It consistently outperforms Logistic Regression across most forward horizons

**4. Evaluation.** ROC-AUC is used as the primary metric. For imbalanced binary classification problems -- where the positive class (injury) is rare -- ROC-AUC evaluates discriminative ability independently of any specific decision threshold. This is appropriate because the optimal threshold depends on the end user's risk tolerance, which varies across use cases

### Prior Iterations

The current approach was informed by earlier experiments, each of which contributed useful lessons:

- **Phase 1 -- Recovery Duration Regression.** A Random Forest Regressor trained to predict total days out from a given injury. This established the project's first baseline and highlighted the difficulty of predicting severe injuries with limited features

- **V1 -- Game-Level Binary Classification.** A Logistic Regression model predicting whether an injury occurs during a specific game. This exposed the fundamental limitation of single-game prediction under extreme class imbalance, and motivated the shift to temporal aggregation

- **Binary Reinjury Model.** A Logistic Regression model predicting whether a player will sustain another injury within 30 days of a current one, using only injury history features (prior count, recency, body region, diagnosis). Trained with a time-based split to respect temporal ordering. Serves as a focused, interpretable sub-model

- **XGBoost with SHAP Explainability.** An XGBoost classifier trained on ever-injured status using anthropometric and positional features. While not directly used for forward prediction, the SHAP analysis revealed which features carry the strongest signal: season year, height, position, and body fat percentage emerged as top predictors, alongside workload-derived variables

---

## Results

### Phase 1: Recovery Duration Regression

| Metric | Value |
|--------|-------|
| Mean Absolute Error | 23.1 days |
| Root Mean Squared Error | 56.6 days |
| R-squared | 0.598 |

The model explains roughly 60% of the variance in recovery durations. The MAE of 23.1 days indicates reasonable average accuracy for a first-pass model, but the substantially higher RMSE reveals that some predictions are far off -- the gap between these two metrics is a signature of high-error outliers, which in this context correspond to severe or season-ending injuries

The primary limitation was a narrow feature set: only basic player attributes and an aggregate injury count were available. The model had no information about injury type, severity, or the player's recent workload leading up to the injury.

### V1: Game-Level Classification

| Metric | Value |
|--------|-------|
| ROC-AUC | 0.73 |
| Precision | 3 - 4% |
| Recall | 66 - 72% |

With a base rate of approximately 1.7% (injuries occur in fewer than 2 out of every 100 games), the practical utility of a per-game classifier is severely constrained. An ROC-AUC of 0.73 indicates discriminative ability modestly above random chance, but the operating characteristics tell the real story: when the model flags a game as "injury likely," it is wrong 96-97% of the time. At higher-precision thresholds, recall drops to the point where most actual injuries are missed entirely.

The key finding was not a failure of modeling but a mismatch of formulation. Single-game features carry insufficient signal for injury prediction. The shift to rolling temporal windows addressed this directly

### V2: Rolling Window Prediction

Gradient Boosting outperforms Logistic Regression across the majority of the 14-day forward horizon. The multi-day probability curve provides a qualitatively different kind of output than prior iterations -- instead of a single binary prediction, the model produces a trajectory showing how injury risk evolves over the coming days.

Feature importance analysis (via SHAP values on the XGBoost variant) surfaces the following as the most influential predictors: season year, physical dimensions (height, weight), body fat percentage, and positional role, alongside the rolling workload aggregates. This is broadly consistent with the sports medicine literature, which identifies workload spikes, body composition, and injury history as the primary modifiable and non-modifiable risk factors.

### Limitations

These results reflect an evolving project with several open challenges:

- **Class imbalance** Injuries are rare events in any short time window. Even with balanced class weights and stratified sampling, the positive class remains underrepresented
- **Feature coverage** Tracking data (speed, distance) is not uniformly available across all seasons and players. Anthropometric data from the Draft Combine is optional and incomplete for some players
- **Temporal generalization** Models trained on historical seasons may not fully generalize to future seasons where playing styles, rules, or medical protocols change
- **Severity stratification** The current model treats all injuries equally. A minor ankle tweak and a torn ACL are both counted as positive events, which limits the clinical interpretability of risk scores

*Planned additions: ROC curves across forward days, feature importance rankings, daily probability curves for sample players, and player workload trend lines overlaid with injury events*

---

## Impact

### Why This Matters

NBA teams spend hundreds of millions of dollars annually on player salaries, and injuries represent the single largest threat to that investment. According to league data, the average NBA team loses approximately 15 - 20 player-games per season to injury. The cost extends beyond salary: diminished playoff positioning, disrupted chemistry, and accelerated wear on replacement players all compound over a season.

Current load management practices are largely reactive. Players are rested based on schedule density (back-to-backs), subjective feel, or blanket policies applied uniformly across rosters. These approaches fail to account for the player-specific risk factors: recent workload trends, physical profile, injury history - that actually drive injury probability.

A data-informed, player-specific risk score shifts the frame from reactive to preventive. Rather than responding to injuries after they occur or applying one-size-fits-all rest schedules, teams can make targeted decisions based on quantified risk.

### Use Cases

- **Medical staff.** Daily injury risk assessments inform return-to-play timelines and identify players entering elevated-risk windows before symptoms manifest. A player whose probability curve is rising steeply over the coming week warrants closer monitoring, even if they currently feel fine

- **Coaching staff.** Load management decisions grounded in player-specific workload trends rather than league-wide heuristics. Instead of resting every player on every back-to-back, a coach can identify which specific players carry elevated risk on a given night

- **Front office.** Roster construction and minute allocation informed by injury risk profiles. In trade evaluation and free agency, understanding a player's structural risk factors adds a dimension beyond traditional scouting

### Differentiation

Most published injury prediction models in sports analytics operate in one of two modes: binary classification (will an injury occur, yes or no) or regression (how long will recovery take). BALL differs in a structural way. By producing a daily probability curve across a configurable time horizon, the model answers a more useful question: not just *whether* an injury might happen, but *when* the risk is highest.

This temporal resolution matters because injury prevention is fundamentally a scheduling problem. A decision-maker does not simply need to know that a player is "at risk" - they need to know whether the risk is concentrated in the next two days (suggesting rest tonight) or building gradually over the next two weeks (suggesting a reduced-minutes plan over several games).

---

## Next Steps

This project is ongoing. The following directions are under consideration or active development:

- **Expanded feature engineering.** Incorporating game context variables such as back-to-back schedules, travel distance, and home/away status. Play-by-play intensity metrics (e.g., frequency of high-impact actions like drives to the basket, contested rebounds, or loose-ball dives) may provide stronger workload signals than box-score aggregates alone

- **Injury-type stratification.** Training separate models for different body regions or injury categories. Knee injuries and ankle sprains likely have different risk profiles and respond to different feature signals. A family of specialized models may outperform a single general-purpose classifier

- **Prospective validation.** Evaluating model performance on fully held-out seasons to assess temporal generalization. The current evaluation uses within-sample splits; true out-of-time validation is necessary before any operational deployment

- **Nested temporal cross-validation.** Replacing simple train/test splits with nested temporal CV to produce more robust and less optimistic performance estimates

- **Ensemble approaches.** Combining the classification models (injury likelihood per day) with regression models (expected recovery duration) into a unified risk framework that captures both the probability and the severity of potential injuries

- **Injury report integration.** The official NBA injury report data (available from 2021 onward) contains daily status updates for every player. Incorporating status trajectory (e.g., a player who has been listed as "questionable" for three consecutive days) as a feature could meaningfully improve short-horizon predictions

- **Dynamic visualization.** An animated visualization showing how the predicted probability curve shifts as the lookback window (X) and forward horizon (Y) are adjusted. This would demonstrate the sensitivity of predictions to temporal configuration and serve as both an explanatory tool and an interface for parameter tuning

---

## Repository Structure

| Directory | Contents |
|-----------|----------|
| `src/ball/models/` | Model training notebooks, feature engineering, and the proof-of-concept Streamlit application |
| `src/ball/scripts/` | Data extraction, transformation scripts, and SQL feature queries |
| `src/ball/exploration/` | Exploratory analysis notebooks (court visualization, data relationship mapping, injury instances) |
| `src/ball/db/` | Database schema definitions and connection utilities |
| `docs/` | Project documentation: database schema, model reference material, phase write-ups, injury report notes |
| `data/` | Sample datasets and reference CSVs |

---

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate
# macOS / Linux
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

Recommended VS Code extensions:

- **Python** -- run notebooks and scripts
- **Jupyter** -- work with .ipynb notebooks directly in VS Code
- **SQLite Viewer** -- browse and query .db files without leaving the editor
