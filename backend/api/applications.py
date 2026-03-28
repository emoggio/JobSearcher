from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.models.application import Application
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uid


class ApplicationCreate(BaseModel):
    job_id: str
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None
    notes: Optional[str] = None


@router.get("")
async def list_applications(request: Request, db: AsyncSession = Depends(get_db)):
    from backend.models.job import Job

    from backend.models.user_job_score import UserJobScore
    from sqlalchemy import and_, func

    user_id = _user_id(request)
    result = await db.execute(
        select(Application, Job.title, Job.company, Job.url, Job.compatibility_score, UserJobScore.score)
        .outerjoin(Job, Application.job_id == Job.id)
        .outerjoin(UserJobScore, and_(UserJobScore.job_id == Application.job_id, UserJobScore.user_id == user_id))
        .where(Application.user_id == user_id)
        .order_by(Application.applied_at.desc())
    )
    rows = result.all()
    apps = []
    for app, title, company, url, global_score, user_score in rows:
        score = user_score if user_score is not None else global_score
        apps.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": title or "Unknown role",
            "job_company": company or "Unknown company",
            "job_url": url,
            "job_score": score,
            "status": app.status,
            "applied_at": app.applied_at,
            "next_action": app.next_action,
            "next_action_date": app.next_action_date,
            "notes": app.notes,
        })
    return apps


@router.post("")
async def create_application(
    request: Request, body: ApplicationCreate, db: AsyncSession = Depends(get_db)
):
    user_id = _user_id(request)
    app = Application(job_id=body.job_id, notes=body.notes, user_id=user_id)
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


@router.patch("/{app_id}")
async def update_application(
    app_id: str, request: Request, body: ApplicationUpdate, db: AsyncSession = Depends(get_db)
):
    user_id = _user_id(request)
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == user_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(app, field, value)
    await db.commit()
    return app


@router.delete("/{app_id}")
async def delete_application(
    app_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    user_id = _user_id(request)
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == user_id)
    )
    app = result.scalar_one_or_none()
    if app:
        await db.delete(app)
        await db.commit()
    return {"status": "deleted"}
