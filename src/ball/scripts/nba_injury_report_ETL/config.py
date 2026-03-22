from datetime import date
from pathlib import Path

START_DATE = date(2021, 10, 19)

DB_PATH = Path(__file__).resolve().parent.parent.parent / "db" / "BALL.db"

PLAYERS_CSV = Path(__file__).resolve().parents[4] / "data" / "1-nba_api" / "players.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Times to try per day, latest-first. Stops at the first successful hit.
# Not every slot will have a PDF — the NBA only publishes when there are updates.
REPORT_TIMES = [
    # ("11", "45", "PM"), 11:45 injury reports only started in 2025-2026 season
    ("11", "00", "PM"),
    ("10", "00", "PM"),
    ("07", "00", "PM"),
    ("06", "00", "PM"),
    ("05", "00", "PM"),
    ("12", "00", "PM"),
    ("10", "00", "AM"),
    ("09", "00", "AM"),
]

SLEEP_BETWEEN_REQUESTS = 1.5  # seconds

VALID_STATUSES = {"Out", "Available", "Questionable", "Doubtful", "Probable", "GTD"}
