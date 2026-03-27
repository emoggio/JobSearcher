from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.models.application import Application
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()


class ApplicationCreate(BaseModel):
    job_id: str
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None
    notes: Optional[str] = None


@router.get("")
async def list_applications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).order_by(Application.applied_at.desc()))
    return result.scalars().all()


@router.post("")
async def create_application(body: ApplicationCreate, db: AsyncSession = Depends(get_db)):
    app = Application(job_id=body.job_id, notes=body.notes)
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


@router.patch("/{app_id}")
async def update_application(app_id: str, body: ApplicationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        return {"error": "not found"}
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(app, field, value)
    await db.commit()
    return app


@router.delete("/{app_id}")
async def delete_application(app_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if app:
        await db.delete(app)
        await db.commit()
    return {"status": "deleted"}
