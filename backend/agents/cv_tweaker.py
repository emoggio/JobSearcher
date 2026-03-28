"""
Parses the uploaded CV (per user) and tailors it for specific job descriptions using Claude.
CVs are stored per-user at cv/<user_id>/parsed.json to keep data isolated.
"""
import json
import logging
import os
from pathlib import Path
from anthropic import AsyncAnthropic
from sqlalchemy import select
from backend.db.database import SessionLocal
from backend.models.job import Job

logger = logging.getLogger(__name__)
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_ROOT = Path(__file__).resolve().parent.parent.parent
CV_DIR = _ROOT / "cv"


def _cv_dir(user_id: str) -> Path:
    """Returns the per-user CV directory, creating it if needed."""
    d = CV_DIR / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _parsed_path(user_id: str) -> Path:
    return _cv_dir(user_id) / "parsed.json"


def _pdf_path(user_id: str, filename: str) -> Path:
    return _cv_dir(user_id) / filename


async def parse_cv(cv_path: str, user_id: str = "legacy") -> dict:
    """Extract structured profile from PDF CV using Claude. Saves to per-user cache."""
    import base64
    with open(cv_path, "rb") as f:
        pdf_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract a structured JSON profile from this CV. Include: "
                            "name, email, phone, summary, skills (list), experience "
                            "(list of {title, company, dates, bullets}), education, "
                            "salary_expectation, languages. Return valid JSON only."
                        ),
                    },
                ],
            }
        ],
    )

    parsed = json.loads(response.content[0].text)
    cache = _parsed_path(user_id)
    cache.write_text(json.dumps(parsed, indent=2))
    logger.info("CV parsed and cached for user %s", user_id)
    return parsed


async def get_current_cv(user_id: str = "legacy") -> dict | None:
    """Load the parsed CV for the given user. Returns None if not uploaded yet."""
    path = _parsed_path(user_id)
    # Legacy fallback: try old single-file location
    legacy_path = CV_DIR / "parsed.json"
    if path.exists():
        return json.loads(path.read_text())
    if user_id == "legacy" and legacy_path.exists():
        return json.loads(legacy_path.read_text())
    return None


async def tweak_cv_for_job(job_id: str, user_id: str = "legacy") -> str:
    """Rewrite CV to maximise fit for a specific job without fabricating experience."""
    cv = await get_current_cv(user_id)
    if not cv:
        return "No CV uploaded yet. Please upload your CV first."

    async with SessionLocal() as db:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

    if not job:
        return "Job not found."

    prompt = f"""You are a professional CV writer specialising in senior management and consulting roles.

Rewrite the candidate's CV to best match the job below. Rules:
- Do NOT fabricate experience or skills
- Reframe existing experience using language from the job description
- Prioritise most relevant roles; condense less relevant ones
- Highlight client-facing, delivery, and leadership achievements
- Keep to 2 pages max
- Output plain text formatted as a professional CV

Candidate CV:
{json.dumps(cv, indent=2)}

Target Job:
Title: {job.title}
Company: {job.company}
Description: {(job.description or '')[:3000]}

Return the tailored CV text only."""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
