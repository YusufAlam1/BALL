"""
Handles the DB schema and writes events to injury_list2.
"""

import sqlite3

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            player_id  INTEGER PRIMARY KEY,
            full_name  TEXT,
            first_name TEXT,
            last_name  TEXT,
            is_active  BOOLEAN,
            birthdate  TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS injury_list2 (
            injury_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            Date         DATE,
            Team         TEXT,
            Acquired     TEXT,
            Relinquished TEXT,
            Notes        TEXT,
            player_name  TEXT,
            player_id    INTEGER,
            body_region  TEXT,
            diagnosis    TEXT,
            status       TEXT,
            UNIQUE (Date, player_name, Team)
        )
        """
    )
    # Safe migration for older DBs that predate these columns
    for col_def in ("diagnosis TEXT", "status TEXT"):
        try:
            conn.execute(f"ALTER TABLE injury_list2 ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass  # Column already exists — safe to ignore

    conn.commit()


def write_events(events: list[dict], conn: sqlite3.Connection) -> None:
    """Insert change events into the injury_list table."""
    if not events:
        return
    conn.executemany(
        """
        INSERT OR IGNORE INTO injury_list2
            (Date, Team, Acquired, Relinquished, Notes, player_name, player_id,
             body_region, diagnosis, status)
        VALUES
            (:Date, :Team, :Acquired, :Relinquished, :Notes, :player_name, :player_id,
             :body_region, :diagnosis, :status)
        """,
        events,
    )
    conn.commit()
