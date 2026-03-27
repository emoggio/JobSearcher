from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from backend.db.database import get_db, SessionLocal
from backend.models.job import Job
from backend.agents.scraper import run_search
from backend.agents.scorer import score_jobs
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter()
_search_state = {"running": False, "last_count": 0, "last_run": None}


async def _run_and_track(db: AsyncSession):
    _search_state["running"] = True
    try:
        count = await run_search(db)
        _search_state["last_count"] = count
        _search_state["last_run"] = datetime.utcnow().isoformat()
    finally:
        _search_state["running"] = False


@router.post("/search")
async def trigger_search(background_tasks: BackgroundTasks):
    """Manually trigger a full job search across all sources."""
    if _search_state["running"]:
        return {"status": "already running"}
    async with SessionLocal() as db:
        background_tasks.add_task(_run_and_track, db)
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
    exclude_gaming: Optional[bool] = True,
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
    if exclude_gaming:
        filters.append(Job.is_gaming == False)  # noqa: E712
    if date_posted:
        delta_map = {"24h": 1, "7d": 7, "14d": 14, "30d": 30}
        days = delta_map.get(date_posted)
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            filters.append(Job.date_posted >= cutoff)

    result = await db.execute(
        select(Job).where(and_(*filters)).order_by(Job.compatibility_score.desc())
    )
    jobs = result.scalars().all()
    return jobs


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


@router.post("/{job_id}/score")
async def score_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Re-score a specific job against the current CV."""
    await score_jobs(db, job_ids=[job_id])
    return {"status": "scored"}
