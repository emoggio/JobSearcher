from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.models.application import Application
from datetime import datetime

router = APIRouter()


@router.get("")
async def get_calendar(db: AsyncSession = Depends(get_db)):
    """Return all upcoming calendar events from applications."""
    result = await db.execute(
        select(Application).where(Application.next_action_date >= datetime.utcnow())
    )
    applications = result.scalars().all()

    events = [
        {
            "id": app.id,
            "job_id": app.job_id,
            "title": app.next_action,
            "date": app.next_action_date,
            "status": app.status,
        }
        for app in applications
        if app.next_action_date
    ]
    events.sort(key=lambda e: e["date"])
    return events
