# from playwright.sync_api import sync_playwright
import pandas as pd
from selenium import webdriver
from datetime import datetime

def fetch_injury_table(url: str) -> pd.DataFrame:
    driver = webdriver.Chrome()
    driver.get(url)
    html = driver.page_source
    driver.quit()
    # Try read_html; if multiple tables return, concatenate and normalize
    dfs = pd.read_html(html)
    df = pd.concat(dfs, ignore_index=True)
    df["source_url"] = url
    df["scraped_at"] = datetime.utcnow().isoformat()
    return df