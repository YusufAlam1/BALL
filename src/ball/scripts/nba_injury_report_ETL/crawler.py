import requests
import pdfplumber
import io

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2025-12-28_11_00PM.pdf", headers=headers, timeout=10)

with pdfplumber.open(io.BytesIO(response.content)) as pdf: #io.BytesIO allows reading without saving to disk
    print(f"PAGE COUNT: {len(pdf.pages)}")
    i = 0
    for page in pdf.pages:
        print(f"\n\n\n{i}: {page.extract_text()}")
        i += 1


new_response = requests.get("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2026-03-06_11_00PM.pdf", headers=headers, timeout=10)

with pdfplumber.open(io.BytesIO(new_response.content)) as pdf: #io.BytesIO allows reading without saving to disk
    print(f"PAGE COUNT: {len(pdf.pages)}")
    i = 0
    for page in pdf.pages:
        print(f"\n\n\n{i}: {page.extract_text()}")
        i += 1

# bad_response = requests.get("https://ak-static.cms.nba.com/referee/injury/Injury-Report_2025-01-01_04_15PM.pdf")
# print(f"\n\n\n BAD RESPONSE: {bad_response.status_code}")

