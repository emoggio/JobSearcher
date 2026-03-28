"""CWJobs scraper using Playwright sync API in a thread pool. Scrapes multiple pages."""
import asyncio
import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from backend.sources._base import clean_salary, parse_date

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)

PAGES_TO_SCRAPE = 3


def _scrape_page(page, url: str, jobs: list, seen_urls: set) -> int:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_selector('[data-testid="job-item"]', timeout=10000)
        except Exception:
            return 0

        cards = page.query_selector_all('[data-testid="job-item"]')
        count = 0
        for card in cards:
            try:
                title_el = card.query_selector("[data-at='job-item-title']")
                company_el = card.query_selector("[data-at='job-item-company-name']")
                location_el = card.query_selector("[data-at='job-item-location']")
                salary_el = card.query_selector("[data-at='job-item-salary-info']")
                date_el = card.query_selector("time")
                link_el = (
                    card.query_selector("a[data-testid='job-item-title']")
                    or card.query_selector("a[data-at='job-item-title']")
                )

                title = title_el.inner_text().strip() if title_el else None
                company = company_el.inner_text().strip() if company_el else None
                if not title or not company:
                    continue

                href = link_el.get_attribute("href") if link_el else None
                full_url = f"https://www.cwjobs.co.uk{href}" if href and href.startswith("/") else href
                if not full_url or full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                location_text = location_el.inner_text().strip() if location_el else None
                salary_text = salary_el.inner_text().strip() if salary_el else ""
                salary_min_v, salary_max_v = clean_salary(salary_text)
                date_text = date_el.inner_text().strip() if date_el else ""

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_text,
                    "url": full_url,
                    "source": "cwjobs",
                    "salary_min": salary_min_v,
                    "salary_max": salary_max_v,
                    "date_posted": parse_date(date_text),
                    "remote": "remote" in (location_text or "").lower(),
                })
                count += 1
            except Exception as e:
                logger.debug("CWJobs card parse error: %s", e)
        return count
    except Exception as e:
        logger.warning("CWJobs page error: %s", e)
        return 0


def _scrape_sync(params: dict) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    keywords = params.get("keywords", "programme manager")
    slug = urllib.parse.quote(keywords)
    location = urllib.parse.quote(params.get("location", "London"))

    jobs = []
    seen_urls: set = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            for page_num in range(1, PAGES_TO_SCRAPE + 1):
                url = (
                    f"https://www.cwjobs.co.uk/jobs/{slug}/in-{location}"
                    f"?postedwithin=30&page={page_num}"
                )
                found = _scrape_page(page, url, jobs, seen_urls)
                logger.debug("CWJobs page %d: %d jobs", page_num, found)
                if found == 0:
                    break
        except Exception as e:
            logger.warning("CWJobs scrape failed: %s", e)
        finally:
            browser.close()

    logger.info("CWJobs: %d jobs scraped", len(jobs))
    return jobs


async def scrape(params: dict) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _scrape_sync, params)
