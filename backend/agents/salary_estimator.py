"""
Estimates salary range for jobs that don't advertise it, using Claude.
"""
import json
import os
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

PROMPT = """You are a UK compensation specialist.

Estimate the salary range for this role based on title, company, location, and description.
Return JSON only: {{"salary_min": int, "salary_max": int, "currency": "GBP"}}

Title: {title}
Company: {company}
Location: {location}
Description excerpt: {description}"""


async def estimate_salary(job_data: dict) -> dict:
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=128,
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(
                    title=job_data.get("title", ""),
                    company=job_data.get("company", ""),
                    location=job_data.get("location", ""),
                    description=(job_data.get("description", ""))[:1000],
                ),
            }
        ],
    )
    try:
        return json.loads(response.content[0].text)
    except Exception:
        return {"salary_min": None, "salary_max": None, "currency": "GBP"}
