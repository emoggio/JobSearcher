"""Glassdoor scraper using Playwright."""
import urllib.parse
from backend.sources._base import clean_salary, parse_date


async def scrape(params: dict) -> list[dict]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []

    keywords = urllib.parse.quote(params.get("keywords", "manager director"))
    location = urllib.parse.quote(params.get("location", "London"))
    url = f"https://www.glassdoor.co.uk/Job/jobs.htm?sc.keyword={keywords}&locT=C&locId=2671&fromAge=30"

    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        cards = await page.query_selector_all('[data-test="jobListing"]')
        for card in cards[:50]:
            try:
                title_el = await card.query_selector('[data-test="job-title"]')
                company_el = await card.query_selector('[data-test="employer-name"]')
                location_el = await card.query_selector('[data-test="emp-location"]')
                salary_el = await card.query_selector('[data-test="detailSalary"]')
                link_el = await card.query_selector("a")

                title = (await title_el.inner_text()).strip() if title_el else None
                company = (await company_el.inner_text()).strip() if company_el else None
                location_text = (await location_el.inner_text()).strip() if location_el else None
                salary_text = (await salary_el.inner_text()).strip() if salary_el else ""
                href = await link_el.get_attribute("href") if link_el else None

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
            except Exception:
                continue

        await browser.close()
    return jobs
