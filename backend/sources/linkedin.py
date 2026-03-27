"""
LinkedIn Jobs scraper using Playwright (headless browser).
Scrapes public job listings — no auth required for search results.
"""
import logging
import urllib.parse
from datetime import datetime
from backend.sources._base import clean_salary, parse_date

logger = logging.getLogger(__name__)


async def scrape(params: dict) -> list[dict]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []

    keywords = urllib.parse.quote(params.get("keywords", "manager director"))
    search_location = urllib.parse.quote(params.get("location", "London"))
    url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={keywords}&location={search_location}"
        f"&f_TPR=r2592000&sortBy=DD"
    )

    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector(".jobs-search__results-list", timeout=10000)

            cards = await page.query_selector_all(".jobs-search__results-list li")
            for card in cards[:50]:
                try:
                    title_el = await card.query_selector(".base-search-card__title")
                    company_el = await card.query_selector(".base-search-card__subtitle")
                    location_el = await card.query_selector(".job-search-card__location")
                    date_el = await card.query_selector("time")
                    link_el = await card.query_selector("a.base-card__full-link")

                    title = (await title_el.inner_text()).strip() if title_el else None
                    company = (await company_el.inner_text()).strip() if company_el else None
                    location_text = (await location_el.inner_text()).strip() if location_el else None
                    date_attr = await date_el.get_attribute("datetime") if date_el else None
                    link = await link_el.get_attribute("href") if link_el else None

                    if not title or not company:
                        continue

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
                except Exception as e:
                    logger.debug("Failed to parse LinkedIn card: %s", e)
                    continue
        except Exception as e:
            logger.warning("LinkedIn scrape failed: %s", e)
        finally:
            await browser.close()

    logger.info("LinkedIn: %d jobs scraped", len(jobs))
    return jobs
