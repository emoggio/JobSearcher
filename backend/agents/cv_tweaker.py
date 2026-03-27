"""
Parses the uploaded CV and tailors it for specific job descriptions using Claude.
"""
import json
import os
from anthropic import AsyncAnthropic
from sqlalchemy import select
from backend.db.database import SessionLocal
from backend.models.job import Job

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
CV_CACHE_PATH = "cv/parsed.json"


def find_cv_pdf() -> str | None:
    """Find the first PDF in the cv/ folder regardless of filename."""
    import glob
    pdfs = glob.glob("cv/*.pdf")
    return pdfs[0] if pdfs else None


async def parse_cv(cv_path: str) -> dict:
    """Extract structured profile from PDF CV using Claude."""
    with open(cv_path, "rb") as f:
        pdf_bytes = f.read()

    import base64
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

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
    os.makedirs("cv", exist_ok=True)
    with open(CV_CACHE_PATH, "w") as f:
        json.dump(parsed, f, indent=2)
    return parsed


async def get_current_cv() -> dict | None:
    if os.path.exists(CV_CACHE_PATH):
        with open(CV_CACHE_PATH) as f:
            return json.load(f)
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
