from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime

def fetch_injury_table(url: str) -> pd.DataFrame:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        html = page.content()
        browser.close()
    # Try read_html; if multiple tables return, concatenate and normalize
    dfs = pd.read_html(html)
    df = pd.concat(dfs, ignore_index=True)
    df["source_url"] = url
    df["scraped_at"] = datetime.utcnow().isoformat()
    return df