from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from backend.agents.cv_tweaker import parse_cv, tweak_cv_for_job, get_current_cv, _cv_dir
from backend.agents.scorer import score_jobs
from backend.db.database import SessionLocal
import aiofiles

router = APIRouter()


def _user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=401, detail="Not authenticated")
    return uid


@router.post("/upload")
async def upload_cv(request: Request, file: UploadFile = File(...)):
    """Upload and parse your CV. Triggers re-scoring of all jobs for the current user."""
    user_id = _user_id(request)
    user_dir = _cv_dir(user_id)
    cv_path = user_dir / file.filename
    async with aiofiles.open(cv_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    parsed = await parse_cv(str(cv_path), user_id=user_id)

    async with SessionLocal() as db:
        await score_jobs(db, user_id=user_id)

    return {"status": "cv uploaded and parsed", "summary": parsed}


@router.get("/current")
async def get_cv(request: Request):
    """Return the parsed current CV profile for the current user."""
    user_id = _user_id(request)
    cv = await get_current_cv(user_id=user_id)
    if not cv:
        raise HTTPException(status_code=404, detail="No CV uploaded yet")
    return cv


@router.delete("/current")
async def delete_cv(request: Request):
    """Delete the current user's parsed CV so they can re-upload."""
    import shutil
    user_id = _user_id(request)
    user_dir = _cv_dir(user_id)
    parsed_path = user_dir / "parsed.json"
    if parsed_path.exists():
        parsed_path.unlink()
    # Also remove any uploaded PDF files
    for f in user_dir.iterdir():
        if f.suffix.lower() in (".pdf", ".docx"):
            f.unlink()
    return {"status": "cv deleted"}


@router.post("/tweak/{job_id}")
async def tweak_cv(job_id: str, request: Request):
    """Return a version of your CV tailored for a specific job."""
    user_id = _user_id(request)
    result = await tweak_cv_for_job(job_id, user_id=user_id)
    return {"tailored_cv": result}
