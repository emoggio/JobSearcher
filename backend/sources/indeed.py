"""
Indeed scraper via RSS feed — no Playwright, no bot detection issues.
RSS endpoint is public and stable, returns up to 25 results per page.
"""
import asyncio
import logging
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx

from backend.sources._base import clean_salary

logger = logging.getLogger(__name__)

PAGES_TO_SCRAPE = 3  # 25 results/page = ~75 jobs per keyword set

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def _parse_rss_date(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return parsedate_to_datetime(text).replace(tzinfo=None)
    except Exception:
        return None


def _salary_from_description(desc: str) -> tuple[int | None, int | None]:
    """Try to extract salary from the HTML description snippet."""
    import re
    # Look for patterns like £90,000, £90k, £90,000 - £120,000
    text = re.sub(r"<[^>]+>", " ", desc)  # strip HTML tags
    return clean_salary(text)


async def scrape(params: dict) -> list[dict]:
    keywords = params.get("keywords", "programme director")
    location = params.get("location", "London")
    salary_min = params.get("salary_min", 90000)

    q = urllib.parse.quote_plus(keywords)
    l_ = urllib.parse.quote_plus(location)

    jobs: list[dict] = []
    seen_urls: set[str] = set()

    async with httpx.AsyncClient(headers=_HEADERS, timeout=30, follow_redirects=True) as client:
        for page_num in range(PAGES_TO_SCRAPE):
            start = page_num * 25
            # salary filter is advisory — Indeed still shows some without it
            url = (
                f"https://uk.indeed.com/rss"
                f"?q={q}&l={l_}&sort=date&fromage=30&start={start}"
                f"&salary={salary_min}%2B"
            )
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except Exception as e:
                logger.warning("Indeed RSS page %d failed: %s", page_num, e)
                break

            try:
                root = ET.fromstring(resp.text)
            except ET.ParseError as e:
                logger.warning("Indeed RSS parse error: %s", e)
                break

            items = root.findall(".//item")
            if not items:
                break  # No more results

            for item in items:
                link = (item.findtext("link") or "").strip()
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)

                raw_title = item.findtext("title") or ""
                # RSS title format: "Job Title - Company Name"
                if " - " in raw_title:
                    title_part, company_part = raw_title.rsplit(" - ", 1)
                else:
                    title_part = raw_title
                    company_part = ""

                title = title_part.strip()
                company = company_part.strip() or None

                description = item.findtext("description") or ""
                pub_date = _parse_rss_date(item.findtext("pubDate"))

                # Pull location from description if possible (it's in the HTML snippet)
                import re
                loc_match = re.search(r"<b>Location</b>:\s*([^<\n]+)", description)
                location_text = loc_match.group(1).strip() if loc_match else location

                sal_min, sal_max = _salary_from_description(description)

                if not title:
                    continue

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_text,
                    "description": re.sub(r"<[^>]+>", " ", description).strip(),
                    "url": link,
                    "source": "indeed",
                    "salary_min": sal_min,
                    "salary_max": sal_max,
                    "date_posted": pub_date,
                    "remote": "remote" in (location_text or "").lower(),
                })

            await asyncio.sleep(0.5)  # polite delay between pages

    logger.info("Indeed RSS: %d jobs scraped", len(jobs))
    return jobs
