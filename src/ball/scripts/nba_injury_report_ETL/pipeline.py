"""
NBA Injury Report ETL — main entry point.

Runs the full pipeline:
  1. Crawl PDFs date by date (fetcher)
  2. Parse each PDF into a state dict (parser)
  3. Diff against previous state (transform)
  4. Write change events to BALL.db (loader)

Usage:
    python pipeline.py
    python pipeline.py --start 2024-01-01
    python pipeline.py --start 2024-01-01 --end 2024-03-01
"""

import argparse
from datetime import date, timedelta

from config import START_DATE
from fetcher import fetch_pdf_for_date
from loader import get_connection, write_events
from parser import parse_pdf
from transform import diff_states


def run(start: date = START_DATE, end: date | None = None) -> None:
    end = end or date.today()

    conn = get_connection()
    print(f"DB connected. Running {start} → {end}")

    previous_state: dict = {}
    current_date = start
    first_pdf_found = False

    while current_date <= end:
        pdf_bytes = fetch_pdf_for_date(current_date)

        if not pdf_bytes:
            print(f"  [{current_date}] No report — skipping")
            current_date += timedelta(days=1)
            continue

        current_state = parse_pdf(pdf_bytes, current_date)

        if not first_pdf_found:
            # Seed: treat every listed player as a new injury entry
            events = [
                {
                    "Date": current_date,
                    "Team": team,
                    "Acquired": None,
                    "Relinquished": player,
                    "Notes": data["reason"],
                    "player_name": player,
                    "player_id": None,
                    "body_region": data["body_region"],
                }
                for (player, team), data in current_state.items()
            ]
            first_pdf_found = True
            print(f"  [{current_date}] Seed — {len(events)} players inserted as initial state")
        else:
            events = diff_states(previous_state, current_state, current_date)
            if events:
                print(f"  [{current_date}] {len(events)} changes")

        write_events(events, conn)
        previous_state = current_state
        current_date += timedelta(days=1)

    conn.close()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NBA Injury Report ETL")
    parser.add_argument("--start", type=date.fromisoformat, default=START_DATE)
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    args = parser.parse_args()
    run(start=args.start, end=args.end)
