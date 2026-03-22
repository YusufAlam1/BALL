"""
Fetch game dates for game_ids in metrics_rows.csv using the NBA stats API
endpoint cumestatsplayergames (MATCHUP contains date as MM/DD/YYYY).
Outputs a CSV: game_id, game_date.
"""
import sys
import pandas as pd
import re
import time
from pathlib import Path

from nba_api.stats.endpoints import cumestatsplayergames
from nba_api.stats.endpoints import leaguegamefinder

# Retry and backoff for API timeouts
MAX_RETRIES = 2
RETRY_DELAY = 5

# Paths
MODEL_LOCK_IN = Path(__file__).resolve().parent
METRICS_CSV = MODEL_LOCK_IN / "metrics_rows.csv"
OUTPUT_CSV = MODEL_LOCK_IN / "game_dates.csv"


def game_id_to_season(gid: int) -> str:
    """Derive NBA season from game_id. E.g. 21500001 -> 0021500001, 21 -> 2021-22."""
    s = str(gid).zfill(10)  # 0021500001
    yy = int(s[2:4])  # 21 -> 2021-22
    return f"20{yy:02d}-{str(yy + 1).zfill(2)}"


def parse_date_from_matchup(matchup: str) -> str | None:
    """Parse MM/DD/YYYY from start of MATCHUP (e.g. '08/13/2020 Kings at Lakers')."""
    if not isinstance(matchup, str) or not matchup.strip():
        return None
    m = re.match(r"(\d{1,2}/\d{1,2}/\d{4})", matchup.strip())
    return m.group(1) if m else None


def main():
    print("Loading metrics_rows.csv...")
    df = pd.read_csv(METRICS_CSV)
    # One row per game_id with a player_id (we need player_id + season for the API)
    game_player = df.groupby("game_id").agg({"player_id": "first"}).reset_index()
    game_player["season"] = game_player["game_id"].apply(game_id_to_season)

    # Unique (player_id, season); process by season so we skip more after first players per season
    player_seasons = (
        game_player[["player_id", "season"]]
        .drop_duplicates()
        .sort_values(["season", "player_id"])
    )
    ps_to_games = (
        game_player.groupby(["player_id", "season"])["game_id"]
        .apply(lambda x: list(x.unique()))
        .to_dict()
    )

    game_id_to_date: dict[int, str] = {}
    n_calls = 0
    for idx, row in player_seasons.iterrows():
        pid, season = int(row["player_id"]), row["season"]
        needed = ps_to_games.get((pid, season), [])
        if not needed:
            continue
        if all(g in game_id_to_date for g in needed):
            continue
        n_calls += 1
        if n_calls <= 3 or n_calls % 20 == 0:
            print(f"  API call {n_calls} (player_id={pid}, season={season})...", flush=True)
        for attempt in range(MAX_RETRIES + 1):
            try:
                ep = cumestatsplayergames.CumeStatsPlayerGames(
                    player_id=str(pid),
                    season=season,
                    season_type_all_star="Regular Season",
                )
                tables = ep.get_data_frames()
                if not tables or tables[0].empty:
                    break
                tbl = tables[0]
                for _, r in tbl.iterrows():
                    gid_str = r["GAME_ID"]
                    matchup = r["MATCHUP"]
                    date_str = parse_date_from_matchup(matchup)
                    if not date_str:
                        continue
                    gid_int = int(gid_str)
                    if gid_int not in game_id_to_date:
                        game_id_to_date[gid_int] = date_str
                break
            except Exception as e:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                print(f"  Warning: player_id={pid} season={season} -> {e}", flush=True)
        time.sleep(0.5)  # Rate limit to avoid blocking

    # Fallback: fill missing dates via LeagueGameFinder (one call per season)
    # Game ID 21500001 = 0021500001; API uses 00215 for 2015-16, 00221 for 2021-22, etc.
    # Fetch a range of seasons so we cover whatever encoding the CSV uses.
    all_game_ids_set = set(df["game_id"].unique())
    missing_ids = [g for g in all_game_ids_set if g not in game_id_to_date]
    if missing_ids:
        # Fetch 2015-16 through 2022-23 so we cover 00215... (2015-16) and 00221... (2021-22) etc.
        seasons_to_fetch = [f"20{yy:02d}-{str(yy+1).zfill(2)}" for yy in range(15, 23)]
        print(f"  Filling {len(missing_ids)} missing dates via LeagueGameFinder...", flush=True)
        for season in seasons_to_fetch:
            try:
                lgf = leaguegamefinder.LeagueGameFinder(
                    season_nullable=season,
                    season_type_nullable="Regular Season",
                    player_or_team_abbreviation="T",
                )
                lgf_df = lgf.get_data_frames()[0]
                if lgf_df.empty or "GAME_ID" not in lgf_df.columns:
                    continue
                # One row per (game, team); drop duplicates by GAME_ID
                for gid_str, gdate in lgf_df[["GAME_ID", "GAME_DATE"]].drop_duplicates("GAME_ID").values:
                    gid_int = int(gid_str)
                    if gid_int in all_game_ids_set and gid_int not in game_id_to_date:
                        game_id_to_date[gid_int] = gdate
            except Exception as e:
                print(f"  LeagueGameFinder {season}: {e}", flush=True)
            time.sleep(0.5)

    # Build output for all unique game_ids from metrics
    all_game_ids = sorted(df["game_id"].unique())
    rows = []
    for gid in all_game_ids:
        rows.append({"game_id": gid, "game_date": game_id_to_date.get(gid, "")})

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUTPUT_CSV, index=False)
    missing = out_df["game_date"].eq("").sum()
    print(f"Wrote {len(out_df)} rows to {OUTPUT_CSV}")
    if missing:
        print(f"  ({missing} game_ids have no date from API)")
    return OUTPUT_CSV


if __name__ == "__main__":
    main()
