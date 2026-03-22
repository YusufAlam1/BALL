"""
Main entry point. Fetches, parses, and loads daily NBA injury reports into BALL.db.

HOW TO RUN THE ETL EXAMPLES:
    1. CD into this directory: `cd src/ball/scripts/nba_injury_report_ETL`
    2. Run the pipeline with desired date range:
        python3 pipeline.py                                        # full backfill from START_DATE
        python3 pipeline.py --start 2026-03-01                     # from a date to today
        python3 pipeline.py --start 2026-03-01 --end 2026-03-05   # specific range
"""

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

from config import START_DATE
from fetcher import fetch_pdf_for_date
from loader import get_connection, write_events
from parser import parse_pdf
from resolver import build_player_index, resolve_player_id
from transform import build_events


def _resolve_events(events: list[dict], player_index: dict) -> None:
    """Fills in player_id for each event in place. Warns for any unmatched names."""
    unmatched = []
    for event in events:
        pid = resolve_player_id(event["player_name"], player_index)
        event["player_id"] = pid
        if pid is None and player_index:
            unmatched.append(event["player_name"])
    if unmatched:
        print(f"  [resolver] No match for: {', '.join(sorted(set(unmatched)))}")


def _log_summary(events: list[dict], curr_date: date) -> None:
    relinquished = [e for e in events if e["Relinquished"]]
    acquired     = [e for e in events if e["Acquired"]]

    print(f"  [{curr_date}] {len(relinquished)} relinquished, {len(acquired)} activated")

    if relinquished:
        e = relinquished[0]
        diagnosis_str = f" | {e['diagnosis']}" if e["diagnosis"] else ""
        print(f"    e.g. OUT  {e['player_name']} ({e['status']}) ({e['Team']}){diagnosis_str}")

    if acquired:
        e = acquired[0]
        print(f"    e.g. BACK {e['player_name']} ({e['Team']})")


# Optional CSV export — uncomment the call in run() to enable
INJURY_REPORTS_DIR = Path(__file__).resolve().parent / "injury_reports"

def export_daily_csv(conn, export_date: date) -> None:
    """Writes all rows for a given date to injury_reports/injury_report_{date}.csv"""
    INJURY_REPORTS_DIR.mkdir(exist_ok=True)
    out_path = INJURY_REPORTS_DIR / f"injury_report_{export_date}.csv"
    cursor = conn.execute(
        "SELECT * FROM injury_list2 WHERE Date = ?", (str(export_date),)
    )
    rows = cursor.fetchall()
    if not rows:
        return
    headers = [desc[0] for desc in cursor.description]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"  [{export_date}] Exported {len(rows)} rows → {out_path.name}")


def run(start: date = START_DATE, end: date | None = None) -> None:
    end = end or date.today()

    conn = get_connection()
    player_index = build_player_index(conn)
    print(f"DB connected. Running {start} → {end}")

    current_date = start

    while current_date <= end:
        pdf_bytes = fetch_pdf_for_date(current_date)

        if not pdf_bytes:
            print(f"  [{current_date}] No report — skipping")
            current_date += timedelta(days=1)
            continue

        current_state = parse_pdf(pdf_bytes, current_date)
        events = build_events(current_state, current_date)

        _resolve_events(events, player_index)
        write_events(events, conn)
        _log_summary(events, current_date)

        # export_daily_csv(conn, current_date)  # uncomment to write CSVs to injury_reports/

        current_date += timedelta(days=1)

    conn.close()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NBA Injury Report ETL")
    parser.add_argument("--start", type=date.fromisoformat, default=START_DATE)
    parser.add_argument("--end",   type=date.fromisoformat, default=None)
    args = parser.parse_args()
    run(start=args.start, end=args.end)
