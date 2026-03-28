"""
Google Jobs / niche startup discoverer.
Searches Google for job postings at smaller companies not on major boards.
Uses Google's job listing rich results and direct site searches.
"""
import asyncio
import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from backend.sources._base import clean_salary

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)

# Niche search queries targeting smaller companies and their career pages
QUERIES = [
    'site:jobs.lever.co "programme director" OR "head of delivery" OR "delivery director" London',
    'site:jobs.ashbyhq.com "programme director" OR "delivery director" London',
    'site:boards.greenhouse.io "programme director" OR "head of delivery" London',
    '"head of delivery" OR "programme director" London startup "apply" -linkedin -indeed -reed site:uk',
]


def _scrape_sync(params: dict) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    jobs = []
    seen_urls = set()
    keywords = params.get("keywords", "programme director")

    # Primary: Google's job search (rich results)
    search_q = f"{keywords} London jobs"
    google_jobs_url = f"https://www.google.co.uk/search?q={urllib.parse.quote(search_q)}&ibp=htl;jobs"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            # Try Google Jobs
            page = browser.new_page(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ))
            page.goto(google_jobs_url, wait_until="networkidle", timeout=30000)

            # Accept cookies if prompted
            try:
                page.click('button:has-text("Accept all")', timeout=3000)
            except Exception:
                pass

            try:
                page.wait_for_selector('[jsname="MKCbgd"]', timeout=8000)
            except Exception:
                pass

            # Google Jobs card selectors
            cards = page.query_selector_all('[jsname="MKCbgd"]')
            if not cards:
                cards = page.query_selector_all('[data-ved][class*="job"]')

            for card in cards[:30]:
                try:
                    card.click()
                    import time; time.sleep(0.3)  # Let detail panel load

                    title_el = page.query_selector('[class*="job-title"], h2[class*="title"], [jsname="r4nke"]')
                    company_el = page.query_selector('[class*="company"], [jsname="R5mgy"]')
                    location_el = page.query_selector('[class*="location"], [jsname="Mf0jyc"]')
                    link_el = page.query_selector('a[href][class*="apply"], a[data-ved]')

                    title = title_el.inner_text().strip() if title_el else None
                    company = company_el.inner_text().strip() if company_el else None

                    if not title or not company:
                        continue

                    href = link_el.get_attribute("href") if link_el else None
                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    location_text = location_el.inner_text().strip() if location_el else "London"

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location_text,
                        "url": href,
                        "source": "google",
                        "remote": "remote" in location_text.lower(),
                    })
                except Exception as e:
                    logger.debug("Google Jobs card error: %s", e)
            page.close()
        except Exception as e:
            logger.warning("Google Jobs scrape failed: %s", e)
        finally:
            browser.close()

    logger.info("Google Jobs: %d jobs found", len(jobs))
    return jobs


async def scrape(params: dict) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _scrape_sync, params)
