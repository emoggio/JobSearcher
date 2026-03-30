"""
Imports a job from any URL provided by the user.
Uses httpx to fetch the page, then Claude to extract structured job data.
"""
import json
import logging
import os
import uuid
from datetime import datetime
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.job import Job
from backend.agents.salary_estimator import estimate_salary
from backend.agents._client import make_client

logger = logging.getLogger(__name__)
client = make_client()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

EXTRACT_PROMPT = """Extract structured job data from this webpage content.
Return a JSON object with these fields (null if not found):
title, company, location, description, salary_min (int GBP), salary_max (int GBP), remote (bool), date_posted (ISO date string or null)

Webpage content:
{content}

Return valid JSON only."""

TEXT_EXTRACT_PROMPT = """Extract structured job data from this text. It may be a job title + company, a pasted job description, or any job-related text.
Return a JSON object with these fields (null if not found):
title, company, location, description, salary_min (int GBP), salary_max (int GBP), remote (bool), date_posted (ISO date string or null)

Text:
{content}

Return valid JSON only."""


async def import_from_text(text: str, db: AsyncSession) -> Job | None:
    """Import a job from free-form text (pasted description, job title + company, etc.)."""
    if not text.strip():
        return None

    job_data: dict = {}
    c = make_client()
    try:
        response = await c.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": TEXT_EXTRACT_PROMPT.format(content=text[:5000])}],
        )
        job_data = json.loads(response.content[0].text)
    except Exception as e:
        logger.warning("Claude text extraction failed: %s", e)

    if not job_data.get("title"):
        # Best-effort parse: "Title - Company - Location"
        parts = [p.strip() for p in text.replace(",", " -").split(" - ") if p.strip()]
        job_data["title"] = parts[0] if parts else text[:100]
        if len(parts) >= 2:
            job_data["company"] = parts[1]
        if len(parts) >= 3:
            job_data["location"] = parts[2]

    if not job_data.get("salary_min") and not job_data.get("salary_max"):
        try:
            estimated = await estimate_salary(job_data)
            job_data["salary_min"] = estimated.get("salary_min")
            job_data["salary_max"] = estimated.get("salary_max")
            job_data["salary_estimated"] = True
        except Exception:
            pass

    job = Job(
        id=str(uuid.uuid4()),
        title=job_data.get("title", "Unknown"),
        company=job_data.get("company", "Unknown"),
        location=job_data.get("location"),
        description=job_data.get("description") or text[:2000],
        salary_min=job_data.get("salary_min"),
        salary_max=job_data.get("salary_max"),
        salary_estimated=job_data.get("salary_estimated", False),
        remote=job_data.get("remote", False),
        url=None,
        source="manual",
        date_posted=None,
        is_active=True,
        is_gaming=False,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info("Imported job from text: '%s' at '%s'", job.title, job.company)
    return job


async def import_from_url(url: str, db: AsyncSession) -> Job | None:
    # Fetch page
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as c:
            resp = await c.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        logger.warning("Failed to fetch URL %s: %s", url, e)
        return None

    # Strip HTML tags for Claude
    try:
        from bs4 import BeautifulSoup
        text = BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)
    except ImportError:
        import re
        text = re.sub(r"<[^>]+>", " ", html)

    text = text[:6000]  # cap context

    # Extract with Claude if key available, else basic parse
    job_data: dict = {}
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                messages=[{"role": "user", "content": EXTRACT_PROMPT.format(content=text)}],
            )
            job_data = json.loads(response.content[0].text)
        except Exception as e:
            logger.warning("Claude extraction failed for %s: %s", url, e)

    if not job_data.get("title"):
        logger.warning("Could not extract job title from %s", url)
        return None

    # Estimate salary if missing
    if not job_data.get("salary_min") and not job_data.get("salary_max"):
        try:
            estimated = await estimate_salary(job_data)
            job_data["salary_min"] = estimated.get("salary_min")
            job_data["salary_max"] = estimated.get("salary_max")
            job_data["salary_estimated"] = True
        except Exception:
            pass

    # Parse date
    date_posted = None
    if job_data.get("date_posted"):
        try:
            date_posted = datetime.fromisoformat(str(job_data["date_posted"])[:10])
        except Exception:
            pass

    job = Job(
        id=str(uuid.uuid4()),
        title=job_data.get("title", "Unknown"),
        company=job_data.get("company", "Unknown"),
        location=job_data.get("location"),
        description=job_data.get("description"),
        salary_min=job_data.get("salary_min"),
        salary_max=job_data.get("salary_max"),
        salary_estimated=job_data.get("salary_estimated", False),
        remote=job_data.get("remote", False),
        url=url,
        source="manual",
        date_posted=date_posted,
        is_active=True,
        is_gaming=False,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info("Imported job '%s' at %s from %s", job.title, job.company, url)
    return job
