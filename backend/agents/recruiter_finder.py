"""
Finds LinkedIn recruiters and hiring managers at companies with active matching roles.
Uses LinkedIn search URLs + Claude to draft personalised outreach messages.
"""
import urllib.parse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.job import Job
from backend.models.recruiter import Recruiter
from backend.agents.cv_tweaker import get_current_cv
from backend.agents._client import make_client

client = make_client()

TARGETS_PROMPT = """Given this job title and company, return a JSON object with these fields:
- department: the team/function this role sits in (e.g. "Engineering", "Product", "Operations", "Finance")
- seniority: the level of the role (e.g. "Senior", "Director", "VP", "Manager", "Lead")
- hiring_manager_titles: list of 2-3 likely titles of the person who would hire for this role
- recruiter_keywords: 2-3 keywords a specialist recruiter for this function would have in their title

Job title: {title}
Company: {company}

Return valid JSON only."""


def _linkedin_url(keywords: str) -> str:
    return f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(keywords)}&origin=GLOBAL_SEARCH_HEADER"


async def _get_targets(job: Job) -> dict:
    """Use Claude to extract department, seniority, and likely people to contact."""
    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": TARGETS_PROMPT.format(
                title=job.title, company=job.company
            )}],
        )
        import json
        return json.loads(response.content[0].text)
    except Exception:
        return {}


async def draft_outreach(cv: dict, job: Job, target_type: str = "recruiter") -> str:
    if target_type == "hiring_manager":
        audience = f"the hiring manager for the {job.title} role"
    else:
        audience = f"a recruiter at {job.company} hiring for {job.title}"

    prompt = f"""Write a concise, professional LinkedIn connection request message (max 300 chars)
from this candidate to {audience}.

Reference the specific role and company. Highlight one directly relevant strength. Feel human, not templated.

Candidate summary: {cv.get('summary', '')}
Key skills: {', '.join(cv.get('skills', [])[:5])}

Return only the message text, no quotes."""

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
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
    targets = await _get_targets(job)

    department = targets.get("department", "")
    recruiter_kw = " OR ".join(f'"{k}"' for k in targets.get("recruiter_keywords", ["recruiter", "talent acquisition"]))
    hm_titles = targets.get("hiring_manager_titles", [])

    # Build 3 targeted searches
    searches = [
        {
            "label": "Internal Recruiter",
            "title": f"Recruiter · {department or job.company}",
            "keywords": f'"{job.company}" ({recruiter_kw}) {department}',
            "type": "recruiter",
        },
        {
            "label": "Hiring Manager",
            "title": hm_titles[0] if hm_titles else "Hiring Manager",
            "keywords": f'"{job.company}" ({" OR ".join(f"{t}" for t in hm_titles[:2]) if hm_titles else "hiring manager"}) {department}',
            "type": "hiring_manager",
        },
        {
            "label": "Team / Peer",
            "title": f"{department} team · {job.company}",
            "keywords": f'"{job.company}" "{department}" {targets.get("seniority", "")}',
            "type": "peer",
        },
    ]

    saved = []
    for s in searches:
        url = _linkedin_url(s["keywords"])
        message = await draft_outreach(cv or {}, job, s["type"])
        rec = Recruiter(
            name=s["label"],
            title=s["title"],
            company=job.company,
            linkedin_url=url,
            job_id=job_id,
            message_draft=message,
            user_id=user_id,
        )
        db.add(rec)
        await db.flush()
        saved.append({
            "id": rec.id,
            "label": s["label"],
            "title": s["title"],
            "company": job.company,
            "role": job.title,
            "linkedin_search_url": url,
            "suggested_message": message,
        })

    await db.commit()
    return saved
