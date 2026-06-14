import pandas as pd
from ball.pipeline import data, config, targets
import numpy as np

# Pipeline version
df_pipe = pd.read_csv("artifacts/dataset.csv")

# V2 script version
df = pd.read_csv(config.SAMPLE_MODEL_INPUT_CSV)
df.columns = [c.lower() for c in df.columns]
gd = pd.read_csv(config.SAMPLE_GAME_DATES_CSV)
gd.columns = [c.lower() for c in gd.columns]
gd["game_date"] = pd.to_datetime(gd["game_date"])
df = df.merge(gd, on="game_id", how="left")
df["minutes"] = df["minutes"].apply(data.parse_minutes)
for c in data.RAW_FEATURES:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
df = df.dropna(subset=["game_date"]).sort_values(["player_id", "game_date"]).reset_index(drop=True)
# V2 logic
AGG_STATS = ["mean", "std", "min", "max"]
LOOKBACK_DAYS = 14
FORWARD_DAYS = 14

feat_cols = []
for stat in AGG_STATS:
    for c in data.RAW_FEATURES:
        if c in df.columns:
            feat_cols.append(f"{c}_{stat}")

rows, target_rows, dates, pids = [], [], [], []
present = [c for c in data.RAW_FEATURES if c in df.columns]

for pid, grp in df.groupby("player_id"):
    grp = grp.sort_values("game_date").reset_index(drop=True)
    injury_dates = grp.loc[grp["is_injured"] == 1, "game_date"].tolist()
    gdates = grp["game_date"].values
    for i in range(len(grp)):
        row_date = grp.iloc[i]["game_date"]
        start = row_date - pd.Timedelta(days=LOOKBACK_DAYS)
        mask = (grp["game_date"] <= row_date) & (grp["game_date"] >= start)
        window = grp.loc[mask, present]
        if window.empty:
            continue
        agg = window.agg(AGG_STATS)
        feat = {}
        for stat in AGG_STATS:
            for c in present:
                v = agg.loc[stat, c]
                feat[f"{c}_{stat}"] = 0.0 if pd.isna(v) else float(v)
        tgt = {}
        for d in range(1, FORWARD_DAYS + 1):
            end = row_date + pd.Timedelta(days=d)
            tgt[f"injured_within_{d}"] = int(any((idt > row_date) and (idt <= end) for idt in injury_dates))
        rows.append(feat)
        target_rows.append(tgt)
        dates.append(row_date)
        pids.append(pid)

Xdf = pd.DataFrame(rows).reindex(columns=feat_cols).fillna(0.0)
Tdf = pd.DataFrame(target_rows)
df_v2 = pd.concat([pd.DataFrame({"player_id": pids, "game_date": dates}), Xdf, Tdf], axis=1)
df_v2["game_date"] = df_v2["game_date"].dt.strftime('%Y-%m-%d')
print(df_pipe.shape)
print(df_v2.shape)

for c in df_v2.columns:
    if not df_pipe[c].equals(df_v2[c]):
        print(f"Mismatch in {c}")
