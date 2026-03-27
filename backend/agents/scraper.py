"""
Orchestrates job scraping across all sources, deduplicates, and stores results.
"""
import asyncio
import logging
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.job import Job
from backend.agents.scorer import score_jobs
from backend.agents.salary_estimator import estimate_salary
from backend.sources import linkedin, indeed, reed, adzuna, glassdoor, totaljobs, cwjobs

logger = logging.getLogger(__name__)

GAMING_KEYWORDS = {
    "game", "games", "gaming", "esports", "e-sports", "epic games",
    "ea ", "electronic arts", "activision", "blizzard", "ubisoft",
    "riot games", "valve", "unity technologies", "unreal",
}

SOURCES = [linkedin, indeed, reed, adzuna, glassdoor, totaljobs, cwjobs]

# Keys returned by salary_estimator that don't map to Job columns
_SALARY_EXTRA_KEYS = {"currency"}

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


def _safe_job_fields(job_data: dict) -> dict:
    """Strip any keys that don't exist on the Job model."""
    from sqlalchemy import inspect
    valid = {c.key for c in inspect(Job).mapper.column_attrs}
    return {k: v for k, v in job_data.items() if k in valid}


async def run_search(db: AsyncSession) -> int:
    """Scrape all sources, deduplicate by URL, persist new jobs, then score."""
    tasks = [source.scrape(SEARCH_PARAMS) for source in SOURCES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    existing_urls: set[str] = set(
        row[0] for row in (await db.execute(select(Job.url))).all() if row[0]
    )

    new_jobs: list[Job] = []
    for source_module, source_result in zip(SOURCES, results):
        if isinstance(source_result, Exception):
            logger.warning("Source %s failed: %s", source_module.__name__, source_result)
            continue
        for job_data in source_result:
            url = job_data.get("url")
            if not url or url in existing_urls:
                continue

            if not job_data.get("salary_min") and not job_data.get("salary_max"):
                try:
                    estimated = await estimate_salary(job_data)
                    # Only copy known salary fields — drop 'currency' etc.
                    job_data["salary_min"] = estimated.get("salary_min")
                    job_data["salary_max"] = estimated.get("salary_max")
                    job_data["salary_estimated"] = True
                except Exception as e:
                    logger.warning("Salary estimation failed for '%s': %s", job_data.get("title"), e)
                    job_data["salary_estimated"] = False

            job = Job(**_safe_job_fields(job_data), is_gaming=is_gaming(job_data))
            db.add(job)
            new_jobs.append(job)
            existing_urls.add(url)

    if new_jobs:
        await db.commit()
        logger.info("Saved %d new jobs", len(new_jobs))

    if new_jobs and os.getenv("ANTHROPIC_API_KEY"):
        try:
            await score_jobs(db)
        except Exception as e:
            logger.warning("Scoring pass failed: %s", e)

    return len(new_jobs)
