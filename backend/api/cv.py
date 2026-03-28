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


@router.get("/list")
async def list_cvs(request: Request):
    """List all CV files uploaded by this user."""
    user_id = _user_id(request)
    user_dir = _cv_dir(user_id)
    parsed_path = user_dir / "parsed.json"

    files = []
    for f in sorted(user_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix.lower() in (".pdf", ".docx"):
            import json as _json
            is_active = False
            if parsed_path.exists():
                try:
                    meta = _json.loads(parsed_path.read_text())
                    is_active = meta.get("_source_file") == f.name
                except Exception:
                    # Fallback: the most recently modified PDF is active
                    is_active = False
            files.append({
                "filename": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "is_active": is_active,
            })

    # If only one file, mark it active
    if len(files) == 1:
        files[0]["is_active"] = True

    return {"files": files, "has_parsed": parsed_path.exists()}


@router.post("/activate/{filename}")
async def activate_cv(filename: str, request: Request):
    """Re-parse a specific uploaded CV file and set it as the active one."""
    import urllib.parse
    filename = urllib.parse.unquote(filename)
    user_id = _user_id(request)
    user_dir = _cv_dir(user_id)
    cv_path = user_dir / filename
    if not cv_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if cv_path.suffix.lower() not in (".pdf", ".docx"):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    parsed = await parse_cv(str(cv_path), user_id=user_id)
    # Tag which file is active so list_cvs can identify it
    import json as _json
    from backend.agents.cv_tweaker import _parsed_path as get_parsed_path
    path = get_parsed_path(user_id)
    data = _json.loads(path.read_text())
    data["_source_file"] = filename
    path.write_text(_json.dumps(data, indent=2))

    async with SessionLocal() as db:
        await score_jobs(db, user_id=user_id)

    return {"status": "activated", "filename": filename, "summary": parsed}


@router.delete("/file/{filename}")
async def delete_cv_file(filename: str, request: Request):
    """Delete a specific uploaded CV file."""
    import urllib.parse
    filename = urllib.parse.unquote(filename)
    user_id = _user_id(request)
    user_dir = _cv_dir(user_id)
    cv_path = user_dir / filename
    if not cv_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    cv_path.unlink()
    # If the deleted file was active, remove parsed.json too
    parsed_path = user_dir / "parsed.json"
    if parsed_path.exists():
        import json as _json
        try:
            meta = _json.loads(parsed_path.read_text())
            if meta.get("_source_file") == filename:
                parsed_path.unlink()
        except Exception:
            pass
    return {"status": "deleted", "filename": filename}


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
