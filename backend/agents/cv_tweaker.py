"""
Parses the uploaded CV and tailors it for specific job descriptions using Claude.
"""
import glob
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

# Anchor paths to repo root (two levels up from this file: agents/ -> backend/ -> root)
_ROOT = Path(__file__).resolve().parent.parent.parent
CV_DIR = _ROOT / "cv"
CV_CACHE_PATH = CV_DIR / "parsed.json"


def find_cv_pdf() -> Path | None:
    """Find the first PDF in the cv/ folder regardless of filename."""
    pdfs = list(CV_DIR.glob("*.pdf"))
    return pdfs[0] if pdfs else None


async def parse_cv(cv_path: str) -> dict:
    """Extract structured profile from PDF CV using Claude."""
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
    CV_DIR.mkdir(exist_ok=True)
    CV_CACHE_PATH.write_text(json.dumps(parsed, indent=2))
    logger.info("CV parsed and cached")
    return parsed


async def get_current_cv() -> dict | None:
    if CV_CACHE_PATH.exists():
        return json.loads(CV_CACHE_PATH.read_text())
    return None


async def tweak_cv_for_job(job_id: str) -> str:
    """Rewrite CV to maximise fit for a specific job without fabricating experience."""
    cv = await get_current_cv()
    if not cv:
        return "No CV uploaded yet."

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
