"""
Wellfound (AngelList) startup job scraper.
Uses Playwright to render the JS-heavy page and tries multiple selector strategies.
"""
import asyncio
import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from backend.sources._base import clean_salary

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)

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

    keywords = params.get("keywords", "programme director")
    location = params.get("location", "London")

    # Wellfound /jobs search — more reliable than role-slug URLs
    q = urllib.parse.quote_plus(keywords)
    loc = urllib.parse.quote_plus(location)
    search_url = f"https://wellfound.com/jobs?q={q}&l={loc}"

    jobs: list[dict] = []
    seen_urls: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        try:
            context = browser.new_context(
                user_agent=_UA,
                viewport={"width": 1440, "height": 900},
                locale="en-GB",
            )
            page = context.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page.goto(search_url, wait_until="networkidle", timeout=35000)

            # Wait for any job-like container to appear
            for selector in [
                '[class*="styles_jobResult"]',
                '[data-test="job-listing"]',
                'a[href*="/jobs/"]',
                '[class*="JobResult"]',
                '[class*="job-card"]',
                'div[class*="listing"]',
            ]:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    break
                except Exception:
                    continue

            # Grab all <a> tags that link to individual job pages
            anchors = page.query_selector_all('a[href*="/jobs/"]')

            for a in anchors[:40]:
                try:
                    href = a.get_attribute("href") or ""
                    if not href or "/jobs/" not in href:
                        continue
                    full_url = (
                        f"https://wellfound.com{href}"
                        if href.startswith("/")
                        else href
                    )
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    # Try to extract text from within the link block
                    text_content = a.inner_text().strip()
                    lines = [l.strip() for l in text_content.splitlines() if l.strip()]

                    if len(lines) < 1:
                        continue

                    title = lines[0]
                    company = lines[1] if len(lines) > 1 else None
                    loc_text = next(
                        (l for l in lines if any(c in l for c in [location, "Remote", "Hybrid"])),
                        location,
                    )
                    salary_text = next(
                        (l for l in lines if "£" in l or "$" in l or "k" in l.lower()),
                        "",
                    )
                    sal_min, sal_max = clean_salary(salary_text) if salary_text else (None, None)

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": loc_text,
                        "url": full_url,
                        "source": "wellfound",
                        "salary_min": sal_min,
                        "salary_max": sal_max,
                        "remote": "remote" in loc_text.lower(),
                    })
                except Exception as e:
                    logger.debug("Wellfound anchor parse error: %s", e)

            context.close()
        except Exception as e:
            logger.warning("Wellfound scrape failed: %s", e)
        finally:
            browser.close()

    logger.info("Wellfound: %d jobs scraped", len(jobs))
    return jobs


async def scrape(params: dict) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _scrape_sync, params)
