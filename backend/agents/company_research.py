"""
Company research agent: uses Claude's knowledge to provide a brief company summary
relevant to a specific job title.
"""
import json
import logging

from backend.agents._client import make_client

logger = logging.getLogger(__name__)

client = make_client()

PROMPT = """Based on your knowledge, provide a brief research summary for {company} as it relates to hiring a {job_title}.

Return JSON only:
{{"size": "5,000+ employees", "stage": "Public / Series D", "known_for": "one sentence", "culture_notes": "one sentence", "red_flags": "one sentence or null", "glassdoor_rating": "4.1/5 or Unknown"}}"""


async def get_company_research(company: str, job_title: str) -> dict:
    """
    Returns a brief research summary for a company as it relates to a specific job title.
    Handles exceptions gracefully, returning an empty dict on failure.
    """
    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(company=company, job_title=job_title),
                }
            ],
        )
        raw = response.content[0].text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning("Company research failed for %s / %s: %s", company, job_title, e)
        return {}
