"""Dump page HTML snippet to inspect actual structure."""
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.sync_api import sync_playwright

TARGET = sys.argv[1] if len(sys.argv) > 1 else "totaljobs"

URLS = {
    "totaljobs": "https://www.totaljobs.com/jobs/programme-director/in-London?postedwithin=30&salary=90000",
    "cwjobs": "https://www.cwjobs.co.uk/jobs/programme-director/in-London?postedwithin=30",
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URLS[TARGET], wait_until="networkidle", timeout=30000)
    print(f"Title: {page.title()}")
    # Dump first 8000 chars of body
    body = page.inner_html("body")
    print(body[:8000])
    browser.close()
