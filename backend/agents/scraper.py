"""
Orchestrates job scraping across all sources, deduplicates, and stores results.
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.job import Job
from backend.agents.scorer import score_jobs
from backend.agents.salary_estimator import estimate_salary
from backend.sources import linkedin, indeed, reed, adzuna, glassdoor, totaljobs

GAMING_KEYWORDS = {
    "game", "games", "gaming", "esports", "e-sports", "epic games",
    "ea ", "electronic arts", "activision", "blizzard", "ubisoft",
    "riot games", "valve", "unity technologies", "unreal",
}

SOURCES = [linkedin, indeed, reed, adzuna, glassdoor, totaljobs]

SEARCH_PARAMS = {
    "keywords": (
        '"Head of Delivery" OR "Programme Director" OR "Delivery Director" OR '
        '"Head of PMO" OR "Senior Programme Manager" OR "Principal Consultant" OR '
        '"Director of Delivery" OR "VP Delivery" OR "Head of Technology Delivery"'
    ),
    "location": "London",
    "salary_min": 90000,
    "date_posted": "30d",
}


def is_gaming(job_data: dict) -> bool:
    text = f"{job_data.get('company', '')} {job_data.get('title', '')} {job_data.get('description', '')}".lower()
    return any(kw in text for kw in GAMING_KEYWORDS)


async def run_search(db: AsyncSession):
    """Scrape all sources, deduplicate by URL, persist new jobs, then score."""
    tasks = [source.scrape(SEARCH_PARAMS) for source in SOURCES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    existing_urls = set(
        row[0] for row in (await db.execute(select(Job.url))).all()
    )

    new_jobs = []
    for source_results in results:
        if isinstance(source_results, Exception):
            continue
        for job_data in source_results:
            if job_data.get("url") in existing_urls:
                continue
            if not job_data.get("salary_min") and not job_data.get("salary_max"):
                try:
                    estimated = await estimate_salary(job_data)
                    job_data.update(estimated)
                    job_data["salary_estimated"] = True
                except Exception:
                    job_data["salary_estimated"] = False

            job = Job(**job_data, is_gaming=is_gaming(job_data))
            db.add(job)
            new_jobs.append(job)
            existing_urls.add(job_data.get("url"))

    await db.commit()

    if new_jobs and os.getenv("ANTHROPIC_API_KEY"):
        try:
            await score_jobs(db)
        except Exception:
            pass

    return len(new_jobs)
