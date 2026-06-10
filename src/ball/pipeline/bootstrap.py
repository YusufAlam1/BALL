"""Build the local SQLite store from the sample CSVs shipped in the repo.

The project's full data lives in Supabase (Postgres); the repo ships one season
(2015-16) of pre-joined model input so the pipeline is reproducible offline.
This loads it into SQLite — the file every container mounts as a volume.

Tables created:
    model_input  — one row per player-game: features + is_injured
                   (the materialized output of proof_of_concept_use_case/
                   model_input_base.sql against the original BALL.db)
    game_dates   — game_id -> game_date
    players      — id/name/birthdate (fuzzy player search in the app)

Usage:
    python -m ball.pipeline.bootstrap [--db PATH] [--force]
"""
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from ball.pipeline import config

TABLES = ("model_input", "game_dates", "players")


def bootstrap(db: Path, force: bool = False) -> None:
    if db.exists() and not force:
        with sqlite3.connect(db) as conn:
            existing = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        if set(TABLES) <= existing:
            print(f"{db} already has tables {TABLES}; use --force to rebuild.")
            return

    db.parent.mkdir(parents=True, exist_ok=True)
    model_input = pd.read_csv(config.SAMPLE_MODEL_INPUT_CSV)
    # Lowercase column names once at load so SQL and pandas agree downstream.
    model_input.columns = [c.lower() for c in model_input.columns]
    game_dates = pd.read_csv(config.SAMPLE_GAME_DATES_CSV)
    game_dates.columns = [c.lower() for c in game_dates.columns]
    players = pd.read_csv(config.SAMPLE_PLAYERS_CSV)
    players.columns = [c.lower() for c in players.columns]

    with sqlite3.connect(db) as conn:
        for name in TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {name}")
        # Row order is preserved (rowid = CSV order); data.load_base relies on it.
        model_input.to_sql("model_input", conn, index=False)
        game_dates.to_sql("game_dates", conn, index=False)
        players.to_sql("players", conn, index=False)
        conn.execute("CREATE INDEX idx_model_input_player ON model_input(player_id)")
        conn.execute("CREATE INDEX idx_model_input_game ON model_input(game_id)")
        conn.execute("CREATE INDEX idx_game_dates_game ON game_dates(game_id)")
        conn.commit()

    print(f"Bootstrapped {db}:")
    print(f"  model_input: {len(model_input)} player-game rows")
    print(f"  game_dates:  {len(game_dates)} games")
    print(f"  players:     {len(players)} players")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=Path, default=None, help="SQLite path (default: $BALL_DB_PATH)")
    ap.add_argument("--force", action="store_true", help="rebuild even if tables exist")
    args = ap.parse_args()
    bootstrap(args.db or config.db_path(), force=args.force)


if __name__ == "__main__":
    main()
