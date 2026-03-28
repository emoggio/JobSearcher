"""
Scores jobs against the user's CV using Claude.
Stores results in UserJobScore (per-user) so multiple users get independent scores.
"""
import asyncio
import json
import logging
import os
import uuid
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.job import Job
from backend.models.user_job_score import UserJobScore
from backend.agents.cv_tweaker import get_current_cv

logger = logging.getLogger(__name__)
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SCORE_PROMPT = """You are an expert recruiter and hiring manager.

Given the candidate's CV profile and a job description, return a JSON object with:
- score: integer 0-100 representing the % likelihood this candidate would get an interview
- reason: one sentence explaining why (key strengths that align)
- suggestion: one concrete sentence on what's MISSING or what to tweak in the CV to improve fit

Be realistic and strict. Score 80+ only for excellent seniority + skills + industry alignment.
Consider: seniority match, skills overlap, industry fit, location, salary, relevance.

CV Profile:
{cv}

{context_block}Job:
Title: {title}
Company: {company}
Location: {location}
Description: {description}

Respond with valid JSON only. Example:
{{"score": 72, "reason": "Strong delivery governance and stakeholder management align well.", "suggestion": "Missing agile/scrum delivery experience that this role requires — add examples from your PMO work."}}"""


async def score_single_job(job: Job, cv_text: str, search_context: str = "") -> dict:
    context_block = f"Candidate preferences and goals:\n{search_context}\n\n" if search_context else ""
    prompt = SCORE_PROMPT.format(
        cv=cv_text,
        context_block=context_block,
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


async def score_jobs(
    db: AsyncSession,
    job_ids: list[str] | None = None,
    user_id: str = "legacy",
):
    cv_profile = await get_current_cv(user_id=user_id)
    if not cv_profile:
        logger.info("No CV found — skipping scoring")
        return

    cv_text = json.dumps(cv_profile)

    # Load user search context (preferences from profile questionnaire / chat)
    search_context = ""
    try:
        from backend.api.profile import get_search_context
        search_context = await get_search_context(db, user_id=user_id)
    except Exception:
        pass

    if job_ids:
        query = select(Job).where(Job.id.in_(job_ids))
    else:
        # Score jobs that have no user-specific score yet
        scored_ids_result = await db.execute(
            select(UserJobScore.job_id).where(UserJobScore.user_id == user_id)
        )
        scored_ids = {row[0] for row in scored_ids_result.all()}
        query = select(Job).where(Job.id.notin_(scored_ids) if scored_ids else True)

    result = await db.execute(query)
    jobs = result.scalars().all()

    if not jobs:
        return

    logger.info("Scoring %d jobs with Claude for user %s…", len(jobs), user_id)
    sem = asyncio.Semaphore(5)

    async def fetch_score(job: Job):
        async with sem:
            return job, await score_single_job(job, cv_text, search_context)

    # Phase 1: fire all API calls concurrently (no DB access)
    raw_results = await asyncio.gather(*[fetch_score(j) for j in jobs], return_exceptions=True)

    # Phase 2: write to DB sequentially (avoids AsyncSession race conditions)
    for item in raw_results:
        if isinstance(item, Exception):
            logger.warning("Scoring failed: %s", item)
            continue
        job, scored = item
        try:
            existing = await db.execute(
                select(UserJobScore).where(
                    UserJobScore.user_id == user_id,
                    UserJobScore.job_id == job.id,
                )
            )
            ujs = existing.scalar_one_or_none()
            if ujs:
                ujs.score = scored["score"]
                ujs.reason = scored["reason"]
                ujs.suggestion = scored["suggestion"]
            else:
                db.add(UserJobScore(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    job_id=job.id,
                    score=scored["score"],
                    reason=scored["reason"],
                    suggestion=scored["suggestion"],
                ))
        except Exception as e:
            logger.warning("DB write failed for job %s (%s): %s", job.id, job.title, e)

    await db.commit()
    logger.info("Scoring complete for user %s", user_id)
