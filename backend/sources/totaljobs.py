"""Totaljobs scraper using httpx + BeautifulSoup."""
import urllib.parse
from backend.sources._base import make_client, clean_salary, parse_date

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


async def scrape(params: dict) -> list[dict]:
    if not BeautifulSoup:
        return []

    keywords = urllib.parse.quote(params.get("keywords", "manager director"))
    location = urllib.parse.quote(params.get("location", "London"))
    url = f"https://www.totaljobs.com/jobs/{keywords}/in-{location}?postedwithin=30&salary={params.get('salary_min', 90000)}"

    async with make_client() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select("article[data-job-id]")

    jobs = []
    for card in cards[:50]:
        try:
            title = card.select_one("[data-at='job-item-title']")
            company = card.select_one("[data-at='job-item-company-name']")
            location_el = card.select_one("[data-at='job-item-location']")
            salary_el = card.select_one("[data-at='job-item-salary-info']")
            date_el = card.select_one("time")
            link = card.select_one("a[data-at='job-item-title']")

            if not title or not company:
                continue

            salary_text = salary_el.get_text(strip=True) if salary_el else ""
            salary_min, salary_max = clean_salary(salary_text)
            location_text = location_el.get_text(strip=True) if location_el else None

            jobs.append({
                "title": title.get_text(strip=True),
                "company": company.get_text(strip=True),
                "location": location_text,
                "url": "https://www.totaljobs.com" + link["href"] if link else None,
                "source": "totaljobs",
                "salary_min": salary_min,
                "salary_max": salary_max,
                "date_posted": parse_date(date_el.get_text(strip=True) if date_el else ""),
                "remote": "remote" in (location_text or "").lower(),
            })
        except Exception:
            continue

    return jobs
