import logging
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from backend.db.database import get_db, SessionLocal
from backend.models.job import Job
from backend.models.user_job_score import UserJobScore
from backend.agents.scraper import run_search
from backend.agents.scorer import score_jobs
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter()

# Per-user search state: {user_id: {running, last_count, last_run, errors}}
_search_state: dict[str, dict] = {}


def _get_state(user_id: str) -> dict:
    if user_id not in _search_state:
        _search_state[user_id] = {
            "running": False, "last_count": 0, "last_run": None,
            "errors": [], "by_source": {}, "source_errors": {},
        }
    return _search_state[user_id]


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uid


async def _run_and_track(user_id: str, deep: bool = False):
    state = _get_state(user_id)
    state["running"] = True
    state["errors"] = []
    try:
        async with SessionLocal() as db:
            result = await run_search(db, user_id=user_id, deep=deep)
        count = result.get("total", 0) if isinstance(result, dict) else result
        state["last_count"] = count
        state["last_run"] = datetime.utcnow().isoformat()
        state["by_source"] = result.get("by_source", {}) if isinstance(result, dict) else {}
        state["source_errors"] = result.get("source_errors", {}) if isinstance(result, dict) else {}
        logger.info("Search complete for user %s — %d new jobs found", user_id, count)
    except Exception as e:
        logger.exception("Search failed for user %s: %s", user_id, e)
        state["errors"].append(str(e))
    finally:
        state["running"] = False


@router.post("/search")
async def trigger_search(request: Request, background_tasks: BackgroundTasks, body: dict = {}):
    user_id = _user_id(request)
    state = _get_state(user_id)
    if state["running"]:
        return {"status": "already running"}
    deep = bool(body.get("deep", False))
    background_tasks.add_task(_run_and_track, user_id, deep)
    return {"status": "search started", "deep": deep}


@router.get("/status")
async def search_status(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = _user_id(request)
    total = await db.scalar(select(func.count()).select_from(Job))
    return {**_get_state(user_id), "total_jobs": total}


@router.get("")
async def list_jobs(
    request: Request,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    date_posted: Optional[str] = Query(None, description="24h | 7d | 14d | 30d"),
    compatibility_min: Optional[float] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    user_id = _user_id(request)
    filters = [Job.is_active == True]  # noqa: E712

    if salary_min:
        filters.append(or_(Job.salary_min >= salary_min, Job.salary_min.is_(None)))
    if salary_max:
        filters.append(or_(Job.salary_max <= salary_max, Job.salary_max.is_(None)))
    if remote is not None:
        filters.append(Job.remote == remote)
    if location:
        filters.append(Job.location.ilike(f"%{location}%"))
    if date_posted:
        delta_map = {"24h": 1, "7d": 7, "14d": 14, "30d": 30}
        days = delta_map.get(date_posted)
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            # For jobs with no date_posted, fall back to date_scraped; exclude truly undated ones
            filters.append(
                or_(
                    Job.date_posted >= cutoff,
                    and_(Job.date_posted.is_(None), Job.date_scraped >= cutoff),
                )
            )

    # Fetch jobs joined with user-specific scores
    result = await db.execute(
        select(Job, UserJobScore)
        .outerjoin(
            UserJobScore,
            and_(UserJobScore.job_id == Job.id, UserJobScore.user_id == user_id),
        )
        .where(and_(*filters))
        .order_by(
            func.coalesce(UserJobScore.score, Job.compatibility_score).desc().nullslast()
        )
    )
    rows = result.all()

    jobs_out = []
    for job, ujs in rows:
        # Prefer user-specific score from UserJobScore, fall back to global local score
        score = ujs.score if ujs else job.compatibility_score
        reason = (ujs.reason if ujs else None) or job.score_reason
        suggestion = (ujs.suggestion if ujs else None) or job.score_suggestion

        if compatibility_min and (score or 0) < compatibility_min:
            continue

        d = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "remote": job.remote,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_estimated": job.salary_estimated,
            "description": job.description,
            "url": job.url,
            "source": job.source,
            "industry": job.industry,
            "date_posted": job.date_posted,
            "date_scraped": job.date_scraped,
            "compatibility_score": score,
            "score_reason": reason,
            "score_suggestion": suggestion,
            "is_active": job.is_active,
            "is_gaming": job.is_gaming,
            "user_notes": job.user_notes,
        }
        jobs_out.append(d)
    return jobs_out


@router.delete("/scores")
async def clear_scores(request: Request, db: AsyncSession = Depends(get_db)):
    """Delete all per-user Claude scores so they get re-scored on next search."""
    from sqlalchemy import delete as sql_delete
    user_id = _user_id(request)
    await db.execute(sql_delete(UserJobScore).where(UserJobScore.user_id == user_id))
    await db.commit()
    return {"status": "scores cleared"}


@router.post("/import")
async def import_job_url(request: Request, background_tasks: BackgroundTasks, body: dict, db: AsyncSession = Depends(get_db)):
    """Import a job from a URL or free-form text, then score it for the current user."""
    from backend.agents.job_importer import import_from_url, import_from_text
    user_id = _user_id(request)
    url = body.get("url", "").strip()
    text = body.get("text", "").strip()

    if url:
        job = await import_from_url(url, db)
        if not job:
            raise HTTPException(
                status_code=422,
                detail="Could not fetch that URL (LinkedIn requires login). Paste the job description text instead."
            )
    elif text:
        job = await import_from_text(text, db)
        if not job:
            raise HTTPException(status_code=422, detail="Could not parse job from text")
    else:
        raise HTTPException(status_code=400, detail="Provide a URL or job text")

    # Score the imported job in the background for this user
    background_tasks.add_task(_score_imported, job.id, user_id)
    return job


async def _score_imported(job_id: str, user_id: str):
    try:
        async with SessionLocal() as db:
            await score_jobs(db, job_ids=[job_id], user_id=user_id)
    except Exception as e:
        logger.warning("Failed to score imported job %s: %s", job_id, e)


@router.post("/{job_id}/cover-letter")
async def get_cover_letter(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    from backend.agents.cover_letter import generate_cover_letter
    user_id = _user_id(request)
    text = await generate_cover_letter(job_id, db, user_id)
    return {"text": text}


@router.post("/{job_id}/interview-prep")
async def get_interview_prep(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    from backend.agents.interview_prep import generate_interview_prep
    user_id = _user_id(request)
    questions = await generate_interview_prep(job_id, db, user_id)
    return {"questions": questions}


@router.get("/{job_id}/company-research")
async def company_research(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    from backend.agents.company_research import get_company_research
    data = await get_company_research(job.company, job.title)
    return data


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}/notes")
async def update_job_notes(job_id: str, request: Request, body: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    job.user_notes = body.get("notes", "")
    await db.commit()
    return {"status": "saved"}


@router.post("/{job_id}/score")
async def score_job(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Re-score a specific job for the current user."""
    user_id = _user_id(request)
    await score_jobs(db, job_ids=[job_id], user_id=user_id)
    return {"status": "scored"}
