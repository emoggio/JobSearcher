"""Glassdoor scraper using Playwright sync API in a thread pool."""
import asyncio
import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from backend.sources._base import clean_salary

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=3)


_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _scrape_sync(params: dict) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    keywords = urllib.parse.quote(params.get("keywords", "manager director"))
    url = f"https://www.glassdoor.co.uk/Job/jobs.htm?sc.keyword={keywords}&locT=C&locId=2671&fromAge=30"

    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        try:
            context = browser.new_context(
                user_agent=_UA,
                viewport={"width": 1366, "height": 768},
                locale="en-GB",
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            cards = page.query_selector_all('[data-test="jobListing"]')
            for card in cards[:50]:
                try:
                    title_el = card.query_selector('[data-test="job-title"]')
                    company_el = card.query_selector('[data-test="employer-name"]')
                    location_el = card.query_selector('[data-test="emp-location"]')
                    salary_el = card.query_selector('[data-test="detailSalary"]')
                    link_el = card.query_selector("a")

                    title = title_el.inner_text().strip() if title_el else None
                    company = company_el.inner_text().strip() if company_el else None
                    location_text = location_el.inner_text().strip() if location_el else None
                    salary_text = salary_el.inner_text().strip() if salary_el else ""
                    href = link_el.get_attribute("href") if link_el else None

                    if not title or not company:
                        continue

                    salary_min, salary_max = clean_salary(salary_text) if salary_text else (None, None)

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location_text,
                        "url": f"https://www.glassdoor.co.uk{href}" if href and href.startswith("/") else href,
                        "source": "glassdoor",
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "remote": "remote" in (location_text or "").lower(),
                    })
                except Exception as e:
                    logger.debug("Glassdoor card parse error: %s", e)
        except Exception as e:
            logger.warning("Glassdoor scrape failed: %s", e)
        finally:
            context.close()
            browser.close()

    logger.info("Glassdoor: %d jobs scraped", len(jobs))
    return jobs


async def scrape(params: dict) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _scrape_sync, params)
