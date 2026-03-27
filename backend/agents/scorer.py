"""
Scores jobs against the user's CV using Claude.
Returns a compatibility % (0–100) representing interview likelihood.
"""
import json
import os
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.job import Job
from backend.agents.cv_tweaker import get_current_cv

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SCORE_PROMPT = """You are an expert recruiter and hiring manager.

Given the candidate's CV profile and a job description, return a JSON object with:
- score: integer 0-100 representing the % likelihood this candidate would get an interview
- reason: one sentence explaining the score

Be realistic and strict. Consider: seniority match, skills overlap, industry fit, location, salary alignment.

CV Profile:
{cv}

Job:
Title: {title}
Company: {company}
Location: {location}
Description: {description}

Respond with valid JSON only. Example: {{"score": 72, "reason": "Strong delivery background but lacks client-facing consulting experience."}}"""


async def score_single_job(job: Job, cv_text: str) -> float:
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
        return float(data.get("score", 0))
    except Exception:
        return 0.0


async def score_jobs(db: AsyncSession, job_ids: list[str] | None = None):
    cv_profile = await get_current_cv()
    if not cv_profile:
        return

    cv_text = json.dumps(cv_profile)

    query = select(Job).where(Job.compatibility_score == None)  # noqa: E711
    if job_ids:
        query = select(Job).where(Job.id.in_(job_ids))

    result = await db.execute(query)
    jobs = result.scalars().all()

    for job in jobs:
        job.compatibility_score = await score_single_job(job, cv_text)

    await db.commit()
