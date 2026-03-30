"""
LinkedIn Jobs scraper using Playwright sync API in a thread pool.
Scrapes multiple pages (start=0, 25, 50...) to get more results.
"""
import asyncio
import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=3)

# Pages to scrape (each page = 25 jobs, so 3 pages = 75 jobs per keyword set)
PAGES_TO_SCRAPE = 3


def _scrape_page(page, url: str, jobs: list, seen_urls: set) -> int:
    """Scrape a single LinkedIn results page. Returns number of jobs found."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_selector(".job-search-card", timeout=10000)
        except Exception:
            return 0

        cards = page.query_selector_all(".job-search-card")
        count = 0
        for card in cards[:25]:
            try:
                title_el = card.query_selector(".base-search-card__title")
                company_el = card.query_selector(".base-search-card__subtitle")
                location_el = card.query_selector(".job-search-card__location")
                date_el = card.query_selector("time")
                link_el = card.query_selector("a.base-card__full-link")

                title = title_el.inner_text().strip() if title_el else None
                company = company_el.inner_text().strip() if company_el else None
                location_text = location_el.inner_text().strip() if location_el else None
                date_attr = date_el.get_attribute("datetime") if date_el else None
                link = link_el.get_attribute("href") if link_el else None

                if not title or not company or not link:
                    continue
                if link in seen_urls:
                    continue
                seen_urls.add(link)

                date_posted = None
                if date_attr:
                    try:
                        date_posted = datetime.fromisoformat(date_attr[:10])
                    except Exception:
                        pass

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_text,
                    "url": link,
                    "source": "linkedin",
                    "date_posted": date_posted,
                    "remote": "remote" in (location_text or "").lower(),
                })
                count += 1
            except Exception as e:
                logger.debug("LinkedIn card parse error: %s", e)
        return count
    except Exception as e:
        logger.warning("LinkedIn page scrape failed: %s", e)
        return 0


def _scrape_sync(params: dict, linkedin_cookie: str | None = None) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    keywords = urllib.parse.quote(params.get("keywords", "manager director"))
    search_location = urllib.parse.quote(params.get("location", "London"))
    base_url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={keywords}&location={search_location}"
        f"&f_TPR=r2592000&sortBy=DD"
    )

    _UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    jobs = []
    seen_urls: set = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = None
        try:
            context = browser.new_context(
                user_agent=_UA,
                viewport={"width": 1440, "height": 900},
                locale="en-GB",
            )
            if linkedin_cookie:
                context.add_cookies([{
                    "name": "li_at",
                    "value": linkedin_cookie,
                    "domain": ".linkedin.com",
                    "path": "/",
                }])
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            for page_num in range(PAGES_TO_SCRAPE):
                start = page_num * 25
                url = f"{base_url}&start={start}"
                found = _scrape_page(page, url, jobs, seen_urls)
                logger.debug("LinkedIn page %d: %d jobs", page_num + 1, found)
                if found == 0:
                    break  # No more results
        except Exception as e:
            logger.warning("LinkedIn scrape failed: %s", e)
        finally:
            if context:
                context.close()
            browser.close()

    logger.info("LinkedIn: %d jobs scraped (%d pages)", len(jobs), PAGES_TO_SCRAPE)
    return jobs


async def scrape(params: dict, linkedin_cookie: str | None = None) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _scrape_sync, params, linkedin_cookie)
