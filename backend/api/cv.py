from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.agents.cv_tweaker import parse_cv, tweak_cv_for_job, get_current_cv, CV_DIR, CV_CACHE_PATH
from backend.agents.scorer import score_jobs
from backend.db.database import SessionLocal
import aiofiles

router = APIRouter()


@router.post("/upload")
async def upload_cv(file: UploadFile = File(...)):
    """Upload and parse your CV. Triggers re-scoring of all jobs."""
    CV_DIR.mkdir(exist_ok=True)
    cv_path = CV_DIR / file.filename
    async with aiofiles.open(cv_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    parsed = await parse_cv(str(cv_path))

    async with SessionLocal() as db:
        await score_jobs(db)

    return {"status": "cv uploaded and parsed", "summary": parsed}


@router.get("/current")
async def get_cv():
    """Return the parsed current CV profile."""
    if not CV_CACHE_PATH.exists():
        raise HTTPException(status_code=404, detail="No CV uploaded yet")
    return await get_current_cv()


@router.post("/tweak/{job_id}")
async def tweak_cv(job_id: str):
    """Return a version of your CV tailored for a specific job."""
    result = await tweak_cv_for_job(job_id)
    return {"tailored_cv": result}
