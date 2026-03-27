from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.logging_config import setup_logging, LOG_PATH
from backend.db.database import init_db
from backend.api import jobs, cv, recruiters, applications, calendar, form

setup_logging()

app = FastAPI(title="Scout", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(cv.router, prefix="/api/cv", tags=["cv"])
app.include_router(recruiters.router, prefix="/api/recruiters", tags=["recruiters"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(form.router, prefix="/api/form", tags=["form"])


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/logs")
async def get_logs(lines: int = 100):
    """Return the last N lines of the log file."""
    try:
        text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
        all_lines = text.splitlines()
        return {"lines": all_lines[-lines:]}
    except FileNotFoundError:
        return {"lines": []}
