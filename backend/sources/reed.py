"""Reed.co.uk scraper — REST API if key set, website scraping otherwise (multi-page)."""
import asyncio
import logging
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from backend.sources._base import clean_salary, parse_date

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)

API_KEY = os.getenv("REED_API_KEY", "")
PAGES_TO_SCRAPE = 3  # 27 jobs/page → up to ~80 results


def _parse_reed_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:19])
    except Exception:
        return parse_date(value)


async def _scrape_api(params: dict) -> list[dict]:
    import base64
    import httpx
    token = base64.b64encode(f"{API_KEY}:".encode()).decode()
    headers = {"Authorization": f"Basic {token}"}
    BASE = "https://www.reed.co.uk/api/1.0/search"
    all_jobs = []
    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        for results_to_skip in range(0, PAGES_TO_SCRAPE * 100, 100):
            resp = await client.get(BASE, params={
                "keywords": params.get("keywords", "manager director"),
                "locationName": params.get("location", "London"),
                "minimumSalary": params.get("salary_min", 90000),
                "resultsToTake": 100,
                "resultsToSkip": results_to_skip,
            })
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                break
            for item in results:
                all_jobs.append({
                    "title": item.get("jobTitle"),
                    "company": item.get("employerName"),
                    "location": item.get("locationName"),
                    "description": item.get("jobDescription"),
                    "url": item.get("jobUrl"),
                    "source": "reed",
                    "salary_min": item.get("minimumSalary"),
                    "salary_max": item.get("maximumSalary"),
                    "date_posted": _parse_reed_date(item.get("date")),
                    "remote": item.get("locationName", "").lower() == "remote",
                })
    return all_jobs


def _scrape_web_page(page, url: str, jobs: list, seen_urls: set) -> int:
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        try:
            page.wait_for_selector('article[data-qa="job-card"]', timeout=10000)
        except Exception:
            return 0

        cards = page.query_selector_all('article[data-qa="job-card"]')
        count = 0
        for card in cards:
            try:
                title_el = card.query_selector('[data-qa="job-card-title"]')
                company_el = card.query_selector('[data-qa="job-posted-by"] a')
                location_el = card.query_selector('[data-qa="job-metadata-location"]')
                salary_el = card.query_selector('[data-qa="job-metadata-salary"]')

                title = title_el.inner_text().strip() if title_el else None
                company = company_el.inner_text().strip() if company_el else None
                if not title or not company:
                    continue

                href = title_el.get_attribute("href") if title_el else None
                full_url = f"https://www.reed.co.uk{href}" if href and href.startswith("/") else href
                if not full_url or full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                location_text = location_el.inner_text().strip() if location_el else None
                salary_text = salary_el.inner_text().strip() if salary_el else ""
                salary_min, salary_max = clean_salary(salary_text)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_text,
                    "url": full_url,
                    "source": "reed",
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "remote": "remote" in (location_text or "").lower(),
                })
                count += 1
            except Exception as e:
                logger.debug("Reed card parse error: %s", e)
        return count
    except Exception as e:
        logger.warning("Reed page error: %s", e)
        return 0


def _scrape_web_sync(params: dict) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    keywords = params.get("keywords", "programme director")
    slug = keywords.lower().replace(" ", "-")
    location = params.get("location", "London").lower()
    salary_from = params.get("salary_min", 90000)

    jobs = []
    seen_urls: set = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            for page_num in range(1, PAGES_TO_SCRAPE + 1):
                url = (
                    f"https://www.reed.co.uk/jobs/{urllib.parse.quote(slug)}-jobs-in-"
                    f"{urllib.parse.quote(location)}"
                    f"?salaryFrom={salary_from}&datecreatedoffset=Month&pageno={page_num}"
                )
                found = _scrape_web_page(page, url, jobs, seen_urls)
                logger.debug("Reed page %d: %d jobs", page_num, found)
                if found == 0:
                    break
        except Exception as e:
            logger.warning("Reed web scrape failed: %s", e)
        finally:
            browser.close()

    logger.info("Reed web: %d jobs scraped", len(jobs))
    return jobs


async def scrape(params: dict) -> list[dict]:
    if API_KEY:
        return await _scrape_api(params)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _scrape_web_sync, params)
