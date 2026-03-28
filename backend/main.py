import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.logging_config import setup_logging, LOG_PATH
from backend.db.database import init_db
from backend.api import jobs, cv, recruiters, applications, calendar, form
from backend.api import auth as auth_router
from backend.api import profile as profile_router

setup_logging()

app = FastAPI(title="Scout", version="1.0.0")

# CORS — configurable for deployment
_cors_origins = os.getenv("SCOUT_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Validate Bearer token on all /api/* routes except /api/auth/* and /health."""
    path = request.url.path
    method = request.method

    if (
        method == "OPTIONS"
        or path == "/health"
        or path.startswith("/api/auth/")
        or not path.startswith("/api/")
    ):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    token = auth_header.removeprefix("Bearer ").strip()
    from backend.api.auth import verify_token
    payload = verify_token(token)
    if not payload:
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

    # Attach user info to request state for use by route handlers
    request.state.user_id = payload.get("sub")
    request.state.username = payload.get("username")

    return await call_next(request)


app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(cv.router, prefix="/api/cv", tags=["cv"])
app.include_router(recruiters.router, prefix="/api/recruiters", tags=["recruiters"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(form.router, prefix="/api/form", tags=["form"])
app.include_router(profile_router.router, prefix="/api/profile", tags=["profile"])


@app.on_event("startup")
async def startup():
    from backend.models import job, application, recruiter, user, user_profile, user_job_score  # noqa: F401
    await init_db()


@app.get("/health")
async def health():
    ai_connected = bool(os.getenv("ANTHROPIC_API_KEY"))
    return {"status": "ok", "ai_connected": ai_connected}


@app.get("/api/logs")
async def get_logs(lines: int = 100):
    try:
        text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
        all_lines = text.splitlines()
        return {"lines": all_lines[-lines:]}
    except FileNotFoundError:
        return {"lines": []}
