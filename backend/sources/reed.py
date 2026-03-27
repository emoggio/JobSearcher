"""Reed.co.uk scraper — uses official REST API."""
import os
import httpx
import base64
from backend.sources._base import parse_date

API_KEY = os.getenv("REED_API_KEY", "")
BASE = "https://www.reed.co.uk/api/1.0/search"


async def scrape(params: dict) -> list[dict]:
    if not API_KEY:
        return []

    token = base64.b64encode(f"{API_KEY}:".encode()).decode()
    headers = {"Authorization": f"Basic {token}"}

    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        resp = await client.get(BASE, params={
            "keywords": params.get("keywords", "manager director"),
            "locationName": params.get("location", "London"),
            "minimumSalary": params.get("salary_min", 90000),
            "resultsToTake": 100,
        })
        resp.raise_for_status()
        data = resp.json()

    jobs = []
    for item in data.get("results", []):
        jobs.append({
            "title": item.get("jobTitle"),
            "company": item.get("employerName"),
            "location": item.get("locationName"),
            "description": item.get("jobDescription"),
            "url": item.get("jobUrl"),
            "source": "reed",
            "salary_min": item.get("minimumSalary"),
            "salary_max": item.get("maximumSalary"),
            "date_posted": parse_date(item.get("date", "")),
            "remote": item.get("locationName", "").lower() == "remote",
        })
    return jobs
