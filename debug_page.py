"""Debug: loads a page with Playwright and dumps element info."""
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.sync_api import sync_playwright

PAGES = {
    "indeed": "https://uk.indeed.com/jobs?q=Programme+Director+Delivery&l=London&sort=date&fromage=30",
    "glassdoor": "https://www.glassdoor.co.uk/Job/jobs.htm?sc.keyword=Programme+Director&locT=C&locId=2671&fromAge=30",
    "totaljobs": "https://www.totaljobs.com/jobs/programme-director/in-London?postedwithin=30&salary=90000",
    "cwjobs": "https://www.cwjobs.co.uk/jobs/programme-director/in-London?postedwithin=30",
}

TARGET = sys.argv[1] if len(sys.argv) > 1 else "indeed"

SELECTORS_TO_TRY = [
    '[data-testid="slider_item"]',
    '[data-testid="jobCard"]',
    '.job_seen_beacon',
    '.jobsearch-ResultsList li',
    'div[class*="job_seen"]',
    'div[class*="tapItem"]',
    '[data-jk]',
    # glassdoor
    '[data-test="jobListing"]',
    'li[data-brandviews]',
    'li.react-job-listing',
    # totaljobs/cwjobs
    'article[data-job-id]',
    'article[class*="job"]',
    '[data-testid="job-card"]',
    'div[class*="job-card"]',
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    url = PAGES[TARGET]
    print(f"Loading: {url}")
    page.goto(url, wait_until="networkidle", timeout=30000)
    print(f"Title: {page.title()}")
    print(f"URL: {page.url}")

    print("\n--- Selector hits ---")
    for sel in SELECTORS_TO_TRY:
        els = page.query_selector_all(sel)
        if els:
            print(f"  FOUND {len(els):3d} x  {sel}")
            if els:
                try:
                    print(f"    First text: {els[0].inner_text()[:120].strip()}")
                except Exception:
                    pass

    browser.close()
