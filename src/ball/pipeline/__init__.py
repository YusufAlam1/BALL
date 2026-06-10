"""Production injury-prediction pipeline, extracted from the V2 research notebooks.

Modules (each with a `python -m ball.pipeline.<module>` CLI where noted):

- bootstrap  — load the sample CSVs into the local SQLite store        [CLI]
- data       — SQLite data access shared by the pipeline and the app
- features   — X-day lookback window aggregation (mean/std/min/max)    [CLI]
- targets    — Y per-forward-day binary target construction
- train      — per-forward-day LogReg + GradientBoosting, temporal split [CLI]
- evaluate   — per-horizon ROC-AUC on the temporal hold-out            [CLI]
- explain    — SHAP feature attribution for a chosen forward day       [CLI]

The math is ported verbatim from
src/ball/models/injury_prediction/v2/evaluate_v2.py; `python -m
ball.pipeline.evaluate` verifies the port against the frozen reference results.
"""
