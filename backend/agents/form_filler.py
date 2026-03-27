"""
Uses Claude to suggest answers to online application form fields
based on the user's CV and the target job description.
"""
import json
import os
from anthropic import AsyncAnthropic
from sqlalchemy import select
from backend.db.database import SessionLocal
from backend.models.job import Job
from backend.agents.cv_tweaker import get_current_cv

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def fill_form(job_id: str, form_url: str, form_fields: list[dict]) -> list[dict]:
    cv = await get_current_cv()
    if not cv:
        return [{"error": "No CV uploaded"}]

    async with SessionLocal() as db:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

    job_context = f"Title: {job.title}\nCompany: {job.company}\nDescription: {(job.description or '')[:2000]}" if job else ""

    fields_text = json.dumps(form_fields, indent=2)

    prompt = f"""You are helping a senior professional complete a job application form.

Fill in each form field appropriately based on the candidate's CV and the target role.
Be concise, professional, and honest. Do not fabricate information.

CV:
{json.dumps(cv, indent=2)}

Target Role:
{job_context}

Form URL: {form_url}

Form Fields:
{fields_text}

Return a JSON array matching the input fields, each with an added "answer" key.
Example: [{{"label": "Why do you want this role?", "type": "textarea", "answer": "..."}}]"""

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        return json.loads(response.content[0].text)
    except Exception:
        return form_fields
