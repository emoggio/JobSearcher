"""
Generates interview preparation questions and suggested answers for a specific job
using the candidate's CV and Claude.
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

INTERVIEW_PREP_PROMPT = """You are an expert interview coach with deep knowledge of hiring practices across industries.

Generate 8 likely interview questions for the candidate applying to this role, along with a suggested answer for each based on their CV. Produce a mix of question types covering:
- behavioural (past experience, how you handled situations)
- technical (role-specific skills and knowledge)
- situational (hypothetical scenarios)
- company (questions about the specific company, its culture, strategy)

Rules:
- Tailor questions to the specific role and company
- Suggested answers must draw on the candidate's actual CV — do NOT fabricate experience
- Answers should be concise but substantive (3-5 sentences)
- Return a JSON array only, no extra commentary

Candidate CV:
{cv}

Target Job:
Title: {title}
Company: {company}
Location: {location}
Description: {description}

Return a JSON array of exactly 8 objects with keys: "question" (str), "answer" (str), "type" (one of "behavioural" | "technical" | "situational" | "company").
Example:
[{{"question": "Tell me about a time you led a cross-functional team.", "answer": "In my role at...", "type": "behavioural"}}]"""


async def generate_interview_prep(job_id: str, db: AsyncSession, user_id: str) -> list[dict]:
    """Generate interview questions and suggested answers for the given job and user's CV."""
    cv = await get_current_cv(user_id=user_id)
    if not cv:
        raise ValueError("No CV found. Please upload your CV first.")

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise ValueError(f"Job {job_id} not found.")

    prompt = INTERVIEW_PREP_PROMPT.format(
        cv=json.dumps(cv, indent=2),
        title=job.title,
        company=job.company,
        location=job.location or "Not specified",
        description=(job.description or "")[:3000],
    )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        raw = response.content[0].text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        questions = json.loads(raw)
        if not isinstance(questions, list):
            raise ValueError("Response is not a JSON array")
        return questions
    except Exception as e:
        logger.warning("Failed to parse interview prep response for job %s: %s", job_id, e)
        return []
