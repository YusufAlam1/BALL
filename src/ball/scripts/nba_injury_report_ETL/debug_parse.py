"""
Quick debug script — fetches one PDF and prints what the parser sees.
Run: python debug_parse.py
"""

from datetime import date
from fetcher import fetch_pdf_for_date
from parser import parse_pdf
import pdfplumber
import io

d = date(2026, 3, 6)
pdf_bytes = fetch_pdf_for_date(d)

if not pdf_bytes:
    print("No PDF found")
else:
    print(f"PDF fetched: {len(pdf_bytes)} bytes\n")

    # Show what extract_table() actually returns (raw)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        print(f"Pages: {len(pdf.pages)}\n")
        page = pdf.pages[0]

        print("--- extract_table() output (first page, first 5 rows) ---")
        table = page.extract_table()
        if table:
            for row in table[:5]:
                print(row)
        else:
            print("extract_table() returned None")

        print("\n--- extract_text() output (first page, first 20 lines) ---")
        text = page.extract_text()
        if text:
            for line in text.split("\n")[:20]:
                print(repr(line))
        else:
            print("extract_text() returned None")

    # Show what parse_pdf returns
    print("\n--- parse_pdf() output (first 5 entries) ---")
    state = parse_pdf(pdf_bytes, d)
    print(f"Total players parsed: {len(state)}")
    for key, val in list(state.items())[:5]:
        print(f"  {key} → {val}")
