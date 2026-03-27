"""Adzuna scraper — uses official REST API."""
import os
import httpx
from backend.sources._base import clean_salary, parse_date

APP_ID = os.getenv("ADZUNA_APP_ID")
API_KEY = os.getenv("ADZUNA_API_KEY")
BASE = "https://api.adzuna.com/v1/api/jobs/gb/search/1"


async def scrape(params: dict) -> list[dict]:
    if not APP_ID or not API_KEY:
        return []

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(BASE, params={
            "app_id": APP_ID,
            "app_key": API_KEY,
            "what": params.get("keywords", "manager director"),
            "where": params.get("location", "London"),
            "salary_min": params.get("salary_min", 90000),
            "results_per_page": 50,
            "sort_by": "date",
            "content-type": "application/json",
        })
        resp.raise_for_status()
        data = resp.json()

    jobs = []
    for item in data.get("results", []):
        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        jobs.append({
            "title": item.get("title"),
            "company": item.get("company", {}).get("display_name"),
            "location": item.get("location", {}).get("display_name"),
            "description": item.get("description"),
            "url": item.get("redirect_url"),
            "source": "adzuna",
            "salary_min": int(salary_min) if salary_min else None,
            "salary_max": int(salary_max) if salary_max else None,
            "date_posted": parse_date(item.get("created", "")),
        })
    return jobs
