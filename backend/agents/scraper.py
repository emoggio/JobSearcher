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
from backend.agents.local_scorer import local_score, local_score_reason, local_score_gaps
from backend.sources import linkedin, indeed, reed, adzuna, glassdoor, totaljobs, cwjobs, wellfound, google_jobs

logger = logging.getLogger(__name__)

GAMING_KEYWORDS = {
    "game", "games", "gaming", "esports", "e-sports", "epic games",
    "ea ", "electronic arts", "activision", "blizzard", "ubisoft",
    "riot games", "valve", "unity technologies", "unreal",
}

SOURCES = [linkedin, indeed, reed, adzuna, glassdoor, totaljobs, cwjobs, wellfound, google_jobs]

# Keys returned by salary_estimator that don't map to Job columns
_SALARY_EXTRA_KEYS = {"currency"}

SEARCH_PARAM_SETS = [
    {"keywords": "Head of Delivery Programme Director", "location": "London", "salary_min": 90000, "date_posted": "30d"},
    {"keywords": "Delivery Director Senior Programme Manager", "location": "London", "salary_min": 90000, "date_posted": "30d"},
    {"keywords": "Head of PMO Principal Consultant delivery", "location": "London", "salary_min": 90000, "date_posted": "30d"},
    {"keywords": "Head of Delivery Programme Director", "location": "Remote", "salary_min": 90000, "date_posted": "30d"},
]


def is_gaming(job_data: dict) -> bool:
    text = f"{job_data.get('company', '')} {job_data.get('title', '')} {job_data.get('description', '')}".lower()
    return any(kw in text for kw in GAMING_KEYWORDS)


def _safe_job_fields(job_data: dict) -> dict:
    """Strip any keys that don't exist on the Job model."""
    from sqlalchemy import inspect
    valid = {c.key for c in inspect(Job).mapper.column_attrs}
    return {k: v for k, v in job_data.items() if k in valid}


async def run_search(db: AsyncSession, user_id: str = "legacy") -> dict:
    """Scrape all sources across multiple keyword sets, deduplicate, persist, score.
    Returns dict with total, by_source counts, and source_errors."""
    source_map = [
        (source, params)
        for params in SEARCH_PARAM_SETS
        for source in SOURCES
    ]
    tasks = [source.scrape(params) for source, params in source_map]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    existing_urls: set[str] = set(
        row[0] for row in (await db.execute(select(Job.url))).all() if row[0]
    )

    # Per-source stats (aggregated across all param sets)
    raw_by_source: dict[str, int] = {}
    source_errors: dict[str, list[str]] = {}

    # Collect all new raw job dicts first
    raw_new: list[dict] = []
    for (source_module, params), source_result in zip(source_map, results):
        source_name = source_module.__name__.split(".")[-1]
        if isinstance(source_result, Exception):
            logger.warning("Source %s (%s) failed: %s", source_name, params["keywords"][:30], source_result)
            source_errors.setdefault(source_name, []).append(str(source_result)[:200])
            continue
        raw_by_source[source_name] = raw_by_source.get(source_name, 0) + len(source_result)
        for job_data in source_result:
            url = job_data.get("url")
            if not url or url in existing_urls:
                continue
            raw_new.append(job_data)
            existing_urls.add(url)

    # Estimate missing salaries concurrently
    sal_sem = asyncio.Semaphore(5)

    async def maybe_estimate(job_data: dict):
        if job_data.get("salary_min") or job_data.get("salary_max"):
            return
        async with sal_sem:
            try:
                est = await estimate_salary(job_data)
                job_data["salary_min"] = est.get("salary_min")
                job_data["salary_max"] = est.get("salary_max")
                job_data["salary_estimated"] = True
            except Exception as e:
                logger.warning("Salary estimation failed for '%s': %s", job_data.get("title"), e)
                job_data["salary_estimated"] = False

    if os.getenv("ANTHROPIC_API_KEY") and raw_new:
        await asyncio.gather(*[maybe_estimate(j) for j in raw_new])

    new_jobs: list[Job] = []
    for job_data in raw_new:
        job = Job(**_safe_job_fields(job_data), is_gaming=is_gaming(job_data))
        # Apply instant local score so UI always shows something immediately
        if job.compatibility_score is None:
            job.compatibility_score = local_score(job_data)
            job.score_reason = local_score_reason(job_data)
            job.score_suggestion = local_score_gaps(job_data)
        db.add(job)
        new_jobs.append(job)

    if new_jobs:
        await db.commit()
        logger.info("Saved %d new jobs", len(new_jobs))

    if new_jobs and os.getenv("ANTHROPIC_API_KEY"):
        try:
            # Pass explicit job IDs and user_id so Claude scores are stored per-user
            await score_jobs(db, job_ids=[j.id for j in new_jobs], user_id=user_id)
        except Exception as e:
            logger.warning("Scoring pass failed: %s", e)

    # Log per-source summary
    for src, cnt in sorted(raw_by_source.items()):
        logger.info("Source %s: %d raw jobs scraped", src, cnt)
    for src, errs in source_errors.items():
        for err in errs:
            logger.warning("Source %s error: %s", src, err)

    return {"total": len(new_jobs), "by_source": raw_by_source, "source_errors": source_errors}
