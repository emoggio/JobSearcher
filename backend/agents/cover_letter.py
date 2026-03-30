"""
Generates a tailored cover letter for a specific job using the candidate's CV and Claude.
"""
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.job import Job
from backend.agents.cv_tweaker import get_current_cv
from backend.agents._client import make_client

logger = logging.getLogger(__name__)
client = make_client()

COVER_LETTER_PROMPT = """You are a professional career coach and writer specialising in crafting compelling cover letters.

Write a professional, tailored cover letter for the candidate applying to this specific role. Follow this structure:
- First paragraph: Why this company and role specifically — show genuine interest and knowledge of the company.
- Second paragraph: Matching experience — highlight the most relevant skills and achievements from the candidate's CV that directly address the role requirements.
- Third paragraph: Closing — express enthusiasm, indicate availability, and include a call to action.

Rules:
- Do NOT fabricate experience or skills
- Reference the specific company name and job title
- Keep the tone professional yet personable
- Return only the cover letter text, no extra commentary

Candidate CV:
{cv}

Target Job:
Title: {title}
Company: {company}
Location: {location}
Description: {description}

Return the cover letter text only."""


async def generate_cover_letter(job_id: str, db: AsyncSession, user_id: str) -> str:
    """Generate a tailored cover letter for the given job and user's CV."""
    cv = await get_current_cv(user_id=user_id)
    if not cv:
        raise ValueError("No CV found. Please upload your CV first.")

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise ValueError(f"Job {job_id} not found.")

    prompt = COVER_LETTER_PROMPT.format(
        cv=json.dumps(cv, indent=2),
        title=job.title,
        company=job.company,
        location=job.location or "Not specified",
        description=(job.description or "")[:3000],
    )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
