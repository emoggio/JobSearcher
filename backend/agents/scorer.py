"""
Scores jobs against the user's CV using Claude.
Returns a compatibility % (0–100) representing interview likelihood.
"""
import json
import logging
import os
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.job import Job
from backend.agents.cv_tweaker import get_current_cv

logger = logging.getLogger(__name__)
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SCORE_PROMPT = """You are an expert recruiter and hiring manager.

Given the candidate's CV profile and a job description, return a JSON object with:
- score: integer 0-100 representing the % likelihood this candidate would get an interview
- reason: one sentence explaining why (strengths)
- suggestion: one concrete sentence on what to tweak in the CV to improve fit

Be realistic and strict. Consider: seniority match, skills overlap, industry fit, location, salary alignment.

CV Profile:
{cv}

Job:
Title: {title}
Company: {company}
Location: {location}
Description: {description}

Respond with valid JSON only. Example:
{{"score": 72, "reason": "Strong delivery governance and stakeholder management align well.", "suggestion": "Lead with client-facing experience and downplay gaming context in your summary."}}"""


async def score_single_job(job: Job, cv_text: str) -> dict:
    prompt = SCORE_PROMPT.format(
        cv=cv_text,
        title=job.title,
        company=job.company,
        location=job.location or "Not specified",
        description=(job.description or "")[:3000],
    )
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        data = json.loads(response.content[0].text)
        return {
            "score": float(data.get("score", 0)),
            "reason": data.get("reason", ""),
            "suggestion": data.get("suggestion", ""),
        }
    except Exception as e:
        logger.warning("Failed to parse score response for job %s: %s", job.id, e)
        return {"score": 0.0, "reason": "", "suggestion": ""}


async def score_jobs(db: AsyncSession, job_ids: list[str] | None = None):
    cv_profile = await get_current_cv()
    if not cv_profile:
        logger.info("No CV found — skipping scoring")
        return

    cv_text = json.dumps(cv_profile)

    if job_ids:
        query = select(Job).where(Job.id.in_(job_ids))
    else:
        query = select(Job).where(Job.compatibility_score == None)  # noqa: E711

    result = await db.execute(query)
    jobs = result.scalars().all()

    if not jobs:
        return

    logger.info("Scoring %d jobs…", len(jobs))
    for job in jobs:
        try:
            result = await score_single_job(job, cv_text)
            job.compatibility_score = result["score"]
            job.score_reason = result["reason"]
            job.score_suggestion = result["suggestion"]
        except Exception as e:
            logger.warning("Scoring failed for job %s (%s): %s", job.id, job.title, e)

    await db.commit()
    logger.info("Scoring complete")
