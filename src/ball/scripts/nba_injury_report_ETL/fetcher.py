"""
Builds NBA injury report URLs and fetches PDF bytes.
"""

import time
from datetime import date

import requests

from config import HEADERS, REPORT_TIMES, SLEEP_BETWEEN_REQUESTS


def build_url(d: date, hour: str, minute: str, meridiem: str) -> str:
    return (
        f"https://ak-static.cms.nba.com/referee/injury/"
        f"Injury-Report_{d.strftime('%Y-%m-%d')}_{hour}_{minute}{meridiem}.pdf"
    )


def fetch_pdf(url: str) -> bytes | None:
    """GET a URL and return raw bytes if it's a PDF, else None."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and "pdf" in r.headers.get("Content-Type", "").lower():
            return r.content
        return None
    except requests.RequestException:
        return None


def fetch_pdf_for_date(d: date) -> bytes | None:
    """
    Try each candidate time for a given date, return the first successful PDF.
    Returns None if no report found for that date.
    """
    for hour, minute, meridiem in REPORT_TIMES:
        url = build_url(d, hour, minute, meridiem)
        pdf_bytes = fetch_pdf(url)
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        if pdf_bytes:
            print(f"  [{d}] Found: {hour}:{minute}{meridiem}")
            return pdf_bytes
    return None
