from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.models.recruiter import Recruiter
from backend.agents.recruiter_finder import find_recruiters_for_job

router = APIRouter()


@router.post("/find/{job_id}")
async def find_recruiters(job_id: str, db: AsyncSession = Depends(get_db)):
    """Find LinkedIn recruiters and hiring managers for a specific job."""
    recruiters = await find_recruiters_for_job(job_id, db)
    return {"found": len(recruiters), "recruiters": recruiters}


@router.get("")
async def list_recruiters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Recruiter).order_by(Recruiter.found_at.desc()))
    return result.scalars().all()


@router.patch("/{recruiter_id}/contacted")
async def mark_contacted(recruiter_id: str, status: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Recruiter).where(Recruiter.id == recruiter_id))
    rec = result.scalar_one_or_none()
    if rec:
        rec.contacted = status
        await db.commit()
    return {"status": "updated"}
