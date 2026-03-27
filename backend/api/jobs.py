import logging
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from backend.db.database import get_db, SessionLocal
from backend.models.job import Job
from backend.agents.scraper import run_search
from backend.agents.scorer import score_jobs
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter()
_search_state = {"running": False, "last_count": 0, "last_run": None, "errors": []}


async def _run_and_track():
    _search_state["running"] = True
    _search_state["errors"] = []
    try:
        async with SessionLocal() as db:
            count = await run_search(db)
        _search_state["last_count"] = count
        _search_state["last_run"] = datetime.utcnow().isoformat()
        logger.info("Search complete — %d new jobs found", count)
    except Exception as e:
        logger.exception("Search failed: %s", e)
        _search_state["errors"].append(str(e))
    finally:
        _search_state["running"] = False


@router.post("/search")
async def trigger_search(background_tasks: BackgroundTasks):
    """Manually trigger a full job search across all sources."""
    if _search_state["running"]:
        return {"status": "already running"}
    background_tasks.add_task(_run_and_track)
    return {"status": "search started"}


@router.get("/status")
async def search_status(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).select_from(Job))
    return {**_search_state, "total_jobs": total}


@router.get("")
async def list_jobs(
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    date_posted: Optional[str] = Query(None, description="24h | 7d | 14d | 30d"),
    compatibility_min: Optional[float] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    filters = [Job.is_active == True]  # noqa: E712

    if salary_min:
        filters.append(Job.salary_min >= salary_min)
    if salary_max:
        filters.append(Job.salary_max <= salary_max)
    if compatibility_min:
        filters.append(Job.compatibility_score >= compatibility_min)
    if remote is not None:
        filters.append(Job.remote == remote)
    if location:
        filters.append(Job.location.ilike(f"%{location}%"))
    if date_posted:
        delta_map = {"24h": 1, "7d": 7, "14d": 14, "30d": 30}
        days = delta_map.get(date_posted)
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            filters.append(Job.date_posted >= cutoff)

    result = await db.execute(
        select(Job).where(and_(*filters)).order_by(Job.compatibility_score.desc().nullslast())
    )
    return result.scalars().all()


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/score")
async def score_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Re-score a specific job against the current CV."""
    await score_jobs(db, job_ids=[job_id])
    return {"status": "scored"}


@router.post("/import")
async def import_job_url(body: dict, db: AsyncSession = Depends(get_db)):
    """Import a job from a URL provided by the user."""
    from backend.agents.job_importer import import_from_url
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL required")
    job = await import_from_url(url, db)
    if not job:
        raise HTTPException(status_code=422, detail="Could not parse job from URL")
    return job
