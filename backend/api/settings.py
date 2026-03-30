from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.models.user import User

router = APIRouter()


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uid


@router.get("")
async def get_settings(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = _user_id(request)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return {"has_linkedin_cookie": bool(user and user.linkedin_cookie)}


@router.post("/linkedin-cookie")
async def save_linkedin_cookie(request: Request, body: dict = Body(...), db: AsyncSession = Depends(get_db)):
    user_id = _user_id(request)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    cookie = body.get("cookie", "").strip()
    user.linkedin_cookie = cookie if cookie else None
    await db.commit()
    return {"status": "saved", "has_linkedin_cookie": bool(cookie)}
