"""
Indeed scraper with stealth mode to bypass bot detection.
Uses --disable-blink-features=AutomationControlled and navigator.webdriver override.
"""
import asyncio
import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from backend.sources._base import clean_salary, parse_date

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=3)

PAGES_TO_SCRAPE = 3  # 15–25 results/page


def _stealth_page(browser):
    """Create a browser page with stealth settings to reduce bot detection."""
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        extra_http_headers={
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        },
    )
    page = context.new_page()
    # Override webdriver flag
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-GB', 'en'] });
    """)
    return page


def _scrape_page(page, url: str, jobs: list, seen_urls: set) -> int:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Check for block page
        title = page.title()
        if "blocked" in title.lower() or "just a moment" in title.lower():
            logger.warning("Indeed: blocked at %s (title: %s)", url, title)
            return -1  # Signal to stop

        cards = page.query_selector_all('[data-testid="slider_item"]')
        if not cards:
            # Try alternative selectors
            cards = page.query_selector_all('.job_seen_beacon') or page.query_selector_all('[class*="job_seen"]')

        count = 0
        for card in cards:
            try:
                title_el = card.query_selector('[data-testid="jobTitle"]') or card.query_selector('h2 a')
                company_el = card.query_selector('[data-testid="company-name"]') or card.query_selector('[class*="companyName"]')
                location_el = card.query_selector('[data-testid="text-location"]') or card.query_selector('[class*="companyLocation"]')
                salary_el = card.query_selector('[data-testid="attribute_snippet_testid"]')
                date_el = card.query_selector('[data-testid="myJobsStateDate"]') or card.query_selector('[class*="date"]')
                link_el = card.query_selector("a[id]") or card.query_selector("h2 a")

                title = title_el.inner_text().strip() if title_el else None
                company = company_el.inner_text().strip() if company_el else None
                location_text = location_el.inner_text().strip() if location_el else None
                salary_text = salary_el.inner_text().strip() if salary_el else ""
                date_text = date_el.inner_text().strip() if date_el else ""
                href = link_el.get_attribute("href") if link_el else None

                if not title or not company:
                    continue

                full_url = f"https://uk.indeed.com{href}" if href and href.startswith("/") else href
                if not full_url or full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                salary_min, salary_max = clean_salary(salary_text) if salary_text else (None, None)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_text,
                    "url": full_url,
                    "source": "indeed",
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "date_posted": parse_date(date_text),
                    "remote": "remote" in (location_text or "").lower(),
                })
                count += 1
            except Exception as e:
                logger.debug("Indeed card parse error: %s", e)
        return count
    except Exception as e:
        logger.warning("Indeed page error: %s", e)
        return 0


def _scrape_sync(params: dict) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    keywords = urllib.parse.quote(params.get("keywords", "manager director"))
    search_location = urllib.parse.quote(params.get("location", "London"))
    salary_min = params.get("salary_min", 90000)

    jobs = []
    seen_urls: set = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            for page_num in range(PAGES_TO_SCRAPE):
                start = page_num * 10
                url = (
                    f"https://uk.indeed.com/jobs"
                    f"?q={keywords}&l={search_location}&sort=date&fromage=30&start={start}"
                    f"&salary={salary_min}%2B"
                )
                page = _stealth_page(browser)
                found = _scrape_page(page, url, jobs, seen_urls)
                page.close()

                if found < 0:  # Blocked
                    break
                if found == 0:
                    break
        except Exception as e:
            logger.warning("Indeed scrape failed: %s", e)
        finally:
            browser.close()

    logger.info("Indeed: %d jobs scraped", len(jobs))
    return jobs


async def scrape(params: dict) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _scrape_sync, params)
