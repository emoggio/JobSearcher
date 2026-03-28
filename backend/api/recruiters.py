from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from backend.db.database import get_db
from backend.models.recruiter import Recruiter
from backend.agents.recruiter_finder import find_recruiters_for_job

router = APIRouter()


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uid


@router.post("/find/{job_id}")
async def find_recruiters(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Find LinkedIn recruiters and hiring managers for a specific job."""
    user_id = _user_id(request)
    recruiters = await find_recruiters_for_job(job_id, db, user_id=user_id)
    return {"found": len(recruiters), "recruiters": recruiters}


@router.get("")
async def list_recruiters(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = _user_id(request)
    result = await db.execute(
        select(Recruiter)
        .where(or_(Recruiter.user_id == user_id, Recruiter.user_id.is_(None)))
        .order_by(Recruiter.found_at.desc())
    )
    return result.scalars().all()


@router.patch("/{recruiter_id}/contacted")
async def mark_contacted(
    recruiter_id: str, status: str, request: Request, db: AsyncSession = Depends(get_db)
):
    user_id = _user_id(request)
    result = await db.execute(
        select(Recruiter).where(
            Recruiter.id == recruiter_id,
            or_(Recruiter.user_id == user_id, Recruiter.user_id.is_(None)),
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    rec.contacted = status
    await db.commit()
    return {"status": "updated"}
