"""
Wellfound (AngelList) startup job scraper using Playwright.
Great for finding smaller tech startups and scale-ups.
"""
import asyncio
import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from backend.sources._base import clean_salary

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)


def _scrape_sync(params: dict) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    keywords = params.get("keywords", "programme director")
    # Wellfound uses role-based filtering — try multiple relevant roles
    roles = ["programme-director", "head-of-delivery", "delivery-manager", "director-of-engineering"]

    jobs = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for role in roles[:2]:  # Limit to 2 roles to keep it fast
                url = f"https://wellfound.com/role/l/{role}/london"
                try:
                    page = browser.new_page()
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    try:
                        page.wait_for_selector('[class*="JobListings"]', timeout=8000)
                    except Exception:
                        # Try alternative selectors
                        pass

                    # Try multiple card selectors
                    cards = (
                        page.query_selector_all('[data-test="StartupResult"]') or
                        page.query_selector_all('[class*="startup-link"]') or
                        page.query_selector_all('a[href*="/jobs/"]')
                    )

                    for card in cards[:30]:
                        try:
                            title_el = (
                                card.query_selector('[class*="title"]') or
                                card.query_selector('[class*="role"]') or
                                card.query_selector('h2') or
                                card.query_selector('h3')
                            )
                            company_el = (
                                card.query_selector('[class*="company"]') or
                                card.query_selector('[class*="startup"]')
                            )

                            title = title_el.inner_text().strip() if title_el else None
                            company = company_el.inner_text().strip() if company_el else None

                            if not title or not company:
                                continue

                            href = card.get_attribute("href") if card.tag_name() == "a" else None
                            if not href:
                                link = card.query_selector("a")
                                href = link.get_attribute("href") if link else None

                            if not href:
                                continue

                            url_full = f"https://wellfound.com{href}" if href.startswith("/") else href
                            if url_full in seen_urls:
                                continue
                            seen_urls.add(url_full)

                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": "London",
                                "url": url_full,
                                "source": "wellfound",
                                "remote": False,
                            })
                        except Exception as e:
                            logger.debug("Wellfound card error: %s", e)
                    page.close()
                except Exception as e:
                    logger.debug("Wellfound role %s failed: %s", role, e)
        except Exception as e:
            logger.warning("Wellfound scrape failed: %s", e)
        finally:
            browser.close()

    logger.info("Wellfound: %d startup jobs scraped", len(jobs))
    return jobs


async def scrape(params: dict) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _scrape_sync, params)
