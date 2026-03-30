from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.models.search_profile import SearchProfile
import json, uuid

router = APIRouter()


def _user_id(request):
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uid


@router.get("")
async def list_profiles(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = _user_id(request)
    result = await db.execute(select(SearchProfile).where(SearchProfile.user_id == user_id))
    profiles = result.scalars().all()
    return [{"id": p.id, "name": p.name, "filters": json.loads(p.filters)} for p in profiles]


@router.post("")
async def create_profile(request: Request, body: dict = Body(...), db: AsyncSession = Depends(get_db)):
    user_id = _user_id(request)
    p = SearchProfile(user_id=user_id, name=body["name"], filters=json.dumps(body.get("filters", {})))
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {"id": p.id, "name": p.name, "filters": json.loads(p.filters)}


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = _user_id(request)
    result = await db.execute(select(SearchProfile).where(SearchProfile.id == profile_id, SearchProfile.user_id == user_id))
    p = result.scalar_one_or_none()
    if p:
        await db.delete(p)
        await db.commit()
    return {"status": "deleted"}
