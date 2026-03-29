"""
User profile questionnaire + chat API.
Each user has their own profile, preferences, and search context.
Claude generates targeted questions and has a chat interface to refine job search.
"""
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.database import get_db
from backend.models.user_profile import UserProfile
from backend.agents._client import make_client as _make_client

logger = logging.getLogger(__name__)
router = APIRouter()


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=401, detail="Not authenticated")
    return uid


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

QUESTIONS_PROMPT = """You are helping a job seeker refine their job search beyond what a CV alone can reveal.

Based on this CV summary, generate exactly 10 short, direct questions that would help tailor the job search.
Focus on:
- Role preferences (individual contributor vs leadership, startup vs enterprise, consulting vs in-house)
- Industry likes/dislikes (what sectors they want to avoid or target)
- Working style (remote preference, travel tolerance, team size preference)
- Career goals (what's the dream job / growth direction)
- Compensation priorities (base vs bonus vs equity vs flexibility)
- Soft constraints (location, notice period, must-haves)
- Past experience gaps they want to fill
- Types of companies they're most excited about

CV:
{cv}

Return a JSON array of 10 question strings. No numbering, no introduction text.
Example: ["What industry sectors excite you most?", "Do you prefer startups or established companies?", ...]"""

CONTEXT_PROMPT = """Based on this CV and the user's Q&A answers, write a 3–4 sentence job search context summary.
This will be injected into job compatibility scoring to give Claude a richer picture of what the candidate wants.

CV: {cv}

Q&A Answers:
{qa}

Write a concise, factual paragraph describing their ideal role, preferences, and priorities.
Focus on what distinguishes their ideal job from an average one. Be specific."""

CHAT_SYSTEM = """You are Scout's job search assistant helping {username} find the best possible job matches.

Your goal is to deeply understand what they want from their next role, what they've loved or hated in the past,
what industries/companies excite them, their preferences on remote/hybrid, company size, growth trajectory,
and anything that would help tailor job recommendations.

You also have access to their CV summary:
{cv_summary}

Current preferences already saved:
{search_context}

Keep responses concise and conversational. After every 2–3 exchanges, summarise any new preferences you've learned
and mention you're updating their profile. Use those updates to refine future scoring.
Ask follow-up questions to dig deeper into their motivations. Be direct, smart, and focused on finding
the RIGHT job — not just any job."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_or_create_profile(db: AsyncSession, user_id: str) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def get_search_context(db: AsyncSession, user_id: str = "legacy") -> str:
    """Returns saved search context for use in scoring prompts."""
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    return (profile.search_context or "") if profile else ""


async def _build_search_context(db: AsyncSession, user_id: str, qa_pairs: list[dict]) -> str:
    from backend.agents.cv_tweaker import get_current_cv

    if not os.getenv("ANTHROPIC_API_KEY") or not qa_pairs:
        return ""

    cv_profile = await get_current_cv(user_id=user_id)
    if not cv_profile:
        return ""

    client = _make_client()
    cv_text = json.dumps(cv_profile)[:3000]
    qa_text = "\n".join(
        f"Q: {p['question']}\nA: {p['answer']}"
        for p in qa_pairs if p.get("answer")
    )
    if not qa_text:
        return ""

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": CONTEXT_PROMPT.format(cv=cv_text, qa=qa_text)}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning("Failed to build search context: %s", e)
        return ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
async def get_profile(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = _user_id(request)
    profile = await _get_or_create_profile(db, user_id)
    return {
        "questions": json.loads(profile.questions or "[]"),
        "qa_pairs": json.loads(profile.qa_pairs or "[]"),
        "search_context": profile.search_context or "",
        "updated_at": profile.updated_at,
    }


@router.post("/generate-questions")
async def generate_questions(request: Request, db: AsyncSession = Depends(get_db)):
    from backend.agents.cv_tweaker import get_current_cv

    user_id = _user_id(request)
    cv_profile = await get_current_cv(user_id=user_id)
    if not cv_profile:
        return {"questions": [], "error": "No CV uploaded yet — please upload your CV first."}

    if not os.getenv("ANTHROPIC_API_KEY"):
        return {"questions": [], "error": "ANTHROPIC_API_KEY not set"}

    client = _make_client()
    cv_text = json.dumps(cv_profile)[:4000]

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": QUESTIONS_PROMPT.format(cv=cv_text)}],
        )
        questions = json.loads(response.content[0].text)
        if not isinstance(questions, list):
            raise ValueError("Expected a JSON array")
    except Exception as e:
        logger.warning("Failed to generate profile questions: %s", e)
        questions = _default_questions()

    profile = await _get_or_create_profile(db, user_id)
    profile.questions = json.dumps(questions)
    await db.commit()
    return {"questions": questions}


class SaveAnswersRequest(BaseModel):
    qa_pairs: list[dict]  # [{question: str, answer: str}]


@router.post("/save-answers")
async def save_answers(
    body: SaveAnswersRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    user_id = _user_id(request)
    profile = await _get_or_create_profile(db, user_id)
    profile.qa_pairs = json.dumps(body.qa_pairs)
    context = await _build_search_context(db, user_id, body.qa_pairs)
    profile.search_context = context
    await db.commit()
    return {"search_context": context, "saved": len(body.qa_pairs)}


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    save_context: Optional[bool] = True


@router.post("/chat")
async def chat(body: ChatRequest, request: Request, db: AsyncSession = Depends(get_db)):
    from backend.agents.cv_tweaker import get_current_cv

    user_id = _user_id(request)
    username = getattr(request.state, "username", user_id)

    if not os.getenv("ANTHROPIC_API_KEY"):
        return {"reply": "No AI API key configured — cannot use chat.", "context_updated": False}

    profile = await _get_or_create_profile(db, user_id)
    search_context = profile.search_context or "None yet."
    cv_profile = await get_current_cv(user_id=user_id)
    cv_summary = json.dumps(cv_profile)[:2000] if cv_profile else "No CV uploaded yet."

    system = CHAT_SYSTEM.format(
        username=username,
        cv_summary=cv_summary,
        search_context=search_context,
    )

    client = _make_client()
    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        reply = response.content[0].text.strip()
    except Exception as e:
        logger.warning("Chat failed: %s", e)
        return {"reply": f"Error: {e}", "context_updated": False}

    context_updated = False
    if body.save_context and len(body.messages) >= 2:
        context_updated = await _update_context_from_chat(
            db, profile, body.messages, reply, cv_summary
        )

    return {"reply": reply, "context_updated": context_updated}


async def _update_context_from_chat(
    db: AsyncSession,
    profile: UserProfile,
    messages: list[ChatMessage],
    last_reply: str,
    cv_summary: str,
) -> bool:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return False

    user_count = sum(1 for m in messages if m.role == "user")
    if user_count % 3 != 0:
        return False

    client = _make_client()
    convo = "\n".join(f"{m.role.upper()}: {m.content}" for m in messages[-8:])
    convo += f"\nASSISTANT: {last_reply}"

    extract_prompt = f"""Based on this conversation, write a concise updated job search profile (3–5 sentences).
Include: target roles, preferred industries/sectors, company types, work style, must-haves, deal-breakers, career goals.

CV: {cv_summary[:1000]}
Conversation:
{convo}
Previous profile: {profile.search_context or "None"}

Write only the updated profile paragraph, no preamble."""

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": extract_prompt}],
        )
        new_context = response.content[0].text.strip()
        if new_context:
            profile.search_context = new_context
            await db.commit()
            return True
    except Exception as e:
        logger.warning("Context update failed: %s", e)
    return False


@router.delete("/data")
async def clear_profile_data(request: Request, db: AsyncSession = Depends(get_db)):
    """Clear all saved Q&A answers and search context for the current user."""
    user_id = _user_id(request)
    profile = await _get_or_create_profile(db, user_id)
    profile.qa_pairs = "[]"
    profile.questions = "[]"
    profile.search_context = ""
    await db.commit()
    return {"status": "profile data cleared"}


def _default_questions() -> list[str]:
    return [
        "What industries excite you most right now (e.g. fintech, SaaS, consulting, public sector)?",
        "Do you prefer working at a startup/scale-up or a large enterprise?",
        "Are you open to consulting/agency roles, or do you prefer in-house positions?",
        "What is your remote work preference (fully remote, hybrid, or office-based)?",
        "What size team do you ideally want to lead or work within?",
        "What salary and compensation package would make you say yes immediately?",
        "Are there specific companies or sectors you definitely want to avoid?",
        "What does your ideal next step look like in 12–18 months?",
        "What types of projects or programmes do you find most energising?",
        "Is there a specific gap in your experience you want your next role to fill?",
    ]
