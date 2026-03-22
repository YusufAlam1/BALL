"""
Fetches the daily NBA injury report PDF.

Reports are published throughout game days in ~15-minute intervals. We only need
the latest one — it has the most current statuses for everyone. We try times from
latest to earliest and stop at the first hit.

URL formats (changed over the years):
    Newer (2025-26+): Injury-Report_YYYY-MM-DD_HH_MMam|pm.pdf  e.g. _11_00PM
    Older (pre-2025):  Injury-Report_YYYY-MM-DD_HHam|pm.pdf     e.g. _11PM
"""

import time
from datetime import date

import requests

from config import HEADERS, REPORT_TIMES, SLEEP_BETWEEN_REQUESTS


def _build_urls(d: date, hour: str, minute: str, meridiem: str) -> list[str]:
    """Returns both URL formats for a given time — newer (with minutes) first, then older."""
    base = f"https://ak-static.cms.nba.com/referee/injury/Injury-Report_{d.strftime('%Y-%m-%d')}"
    return [
        f"{base}_{hour}_{minute}{meridiem}.pdf",  # newer format: _11_00PM
        f"{base}_{hour}{meridiem}.pdf",            # older format: _11PM
    ]


def fetch_pdf(url: str) -> bytes | None:
    """Returns raw PDF bytes if the URL resolves, otherwise None."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and "pdf" in r.headers.get("Content-Type", "").lower():
            return r.content
        return None
    except requests.RequestException:
        return None


def fetch_pdf_for_date(d: date) -> bytes | None:
    """Tries each time slot latest-first and returns the first PDF found, or None if no games that day."""
    for hour, minute, meridiem in REPORT_TIMES:
        for url in _build_urls(d, hour, minute, meridiem):
            pdf_bytes = fetch_pdf(url)
            time.sleep(SLEEP_BETWEEN_REQUESTS)
            if pdf_bytes:
                print(f"  [{d}] Found: {hour}:{minute}{meridiem}")
                return pdf_bytes

    return None
