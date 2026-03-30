"""
Skills gap aggregator: compares high-match job requirements against the user's CV
and surfaces the most important missing or weak skills.
"""
import json
import logging

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents._client import make_client
from backend.agents.cv_tweaker import get_current_cv
from backend.models.job import Job
from backend.models.user_job_score import UserJobScore

logger = logging.getLogger(__name__)

client = make_client()

PROMPT = """Given this CV and these high-match job descriptions/titles, identify the top 5-8 skills or keywords that appear repeatedly in these jobs but are missing or weak in the CV.

For each gap, provide: skill name, frequency (how many jobs mention it), priority (high/medium/low), and a one-line suggestion.

Return JSON only:
{{"gaps": [{{"skill": "string", "frequency": 1, "priority": "high", "suggestion": "string"}}]}}

CV:
{cv}

High-match jobs:
{jobs}"""


async def analyse_skills_gap(db: AsyncSession, user_id: str) -> dict:
    """
    Fetches all jobs with a UserJobScore >= 65 for this user, compares them
    against the user's CV, and returns identified skill gaps.
    """
    # Fetch high-match jobs joined with user scores
    result = await db.execute(
        select(Job, UserJobScore)
        .join(UserJobScore, and_(UserJobScore.job_id == Job.id, UserJobScore.user_id == user_id))
        .where(UserJobScore.score >= 65)
    )
    rows = result.all()

    if not rows:
        return {"gaps": [], "message": "No high-match jobs found (score >= 65). Run a search and score jobs first."}

    # Fetch user CV
    cv = await get_current_cv(user_id=user_id)
    if not cv:
        return {"gaps": [], "message": "No CV uploaded yet. Please upload your CV first."}

    # Build job context: title + first 500 chars of description, cap total at 4000 chars
    job_snippets = []
    total_chars = 0
    for job, _ in rows:
        snippet = f"Title: {job.title}\n{(job.description or '')[:500]}"
        if total_chars + len(snippet) > 4000:
            break
        job_snippets.append(snippet)
        total_chars += len(snippet)

    jobs_text = "\n\n---\n\n".join(job_snippets)
    cv_text = json.dumps(cv)[:2000]

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(cv=cv_text, jobs=jobs_text),
                }
            ],
        )
        raw = response.content[0].text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning("Skills gap analysis failed: %s", e)
        return {"gaps": [], "error": str(e)}
