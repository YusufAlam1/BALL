"""
Writes change events to the injury_list table in BALL.db.
"""

import sqlite3

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create the injury_list table if it doesn't exist yet."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS injury_list (
            injury_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            Date        DATE,
            Team        TEXT,
            Acquired    TEXT,
            Relinquished TEXT,
            Notes       TEXT,
            player_name TEXT,
            player_id   REAL,
            body_region TEXT
        )
        """
    )
    conn.commit()


def write_events(events: list[dict], conn: sqlite3.Connection) -> None:
    """Insert change events into the injury_list table."""
    if not events:
        return
    conn.executemany(
        """
        INSERT INTO injury_list (Date, Team, Acquired, Relinquished, Notes, player_name, player_id, body_region)
        VALUES (:Date, :Team, :Acquired, :Relinquished, :Notes, :player_name, :player_id, :body_region)
        """,
        events,
    )
    conn.commit()
