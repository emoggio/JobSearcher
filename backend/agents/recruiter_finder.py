"""
Finds LinkedIn recruiters and hiring managers at companies with active matching roles.
Uses LinkedIn search URLs + Claude to draft personalised outreach messages.
"""
import os
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.job import Job
from backend.models.recruiter import Recruiter
from backend.agents.cv_tweaker import get_current_cv
from backend.agents._client import make_client

client = make_client()


def linkedin_search_url(company: str, role: str) -> str:
    """Build a LinkedIn people search URL for recruiters at a company."""
    import urllib.parse
    query = urllib.parse.quote(f'"{company}" recruiter OR "talent acquisition" OR "hiring manager" {role}')
    return f"https://www.linkedin.com/search/results/people/?keywords={query}"


async def draft_outreach(cv: dict, job: Job) -> str:
    prompt = f"""Write a concise, professional LinkedIn connection request message (max 300 chars)
from this candidate to a recruiter at {job.company} who is hiring for a {job.title} role.

The message should feel personal, reference the role, and highlight one relevant strength.

Candidate summary: {cv.get('summary', '')}
Key skills: {', '.join(cv.get('skills', [])[:5])}

Return only the message text."""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


async def find_recruiters_for_job(job_id: str, db: AsyncSession, user_id: str = "legacy") -> list[dict]:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return []

    cv = await get_current_cv(user_id=user_id)
    message = await draft_outreach(cv or {}, job)
    search_url = linkedin_search_url(job.company, job.title)

    # Persist as a recruiter lead (LinkedIn search — user clicks through manually)
    recruiter = Recruiter(
        name="LinkedIn Search",
        title="Recruiter / Hiring Manager",
        company=job.company,
        linkedin_url=search_url,
        job_id=job_id,
        message_draft=message,
        user_id=user_id,
    )
    db.add(recruiter)
    await db.commit()
    await db.refresh(recruiter)

    return [
        {
            "id": recruiter.id,
            "company": job.company,
            "role": job.title,
            "linkedin_search_url": search_url,
            "suggested_message": message,
        }
    ]
