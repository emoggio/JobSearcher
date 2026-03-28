# Scout

Self-hosted AI-powered job search platform. Scrapes multiple job boards, scores roles against your CV using Claude, surfaces LinkedIn recruiters, and helps you track and apply — all from a private web dashboard.

## Features

| | |
|---|---|
| **Multi-source scraping** | LinkedIn, Indeed, Reed, Adzuna, Glassdoor, TotalJobs, CWJobs, Wellfound, Google Jobs |
| **AI compatibility scoring** | Claude scores each job 0–100 based on your CV + personal preferences |
| **Gap analysis** | Explains exactly what's missing from your CV for each role |
| **Salary estimation** | AI-estimated salary where not listed |
| **Profile chat** | Chat with Claude to refine your search criteria (saved and used in scoring) |
| **CV tailoring** | Claude rewrites your CV to match a specific job |
| **Recruiter finder** | LinkedIn search links + personalised outreach message for each role |
| **Application tracker** | Status board with notes, next actions, and dates |
| **Multi-user** | Each user has fully isolated data (CV, scores, preferences, applications) |
| **Source health debug** | See how many jobs each source returned and which ones are broken |

## Stack

- **Backend** — Python 3.12 + FastAPI + SQLite (async)
- **Frontend** — React 18 + TypeScript + Tailwind CSS + Vite
- **AI** — Anthropic Claude (`claude-sonnet-4-6`)
- **Scraping** — Playwright (JS-rendered sites) + httpx (APIs)
- **Auth** — HMAC-SHA256 signed tokens, DB-backed users, one-time recovery codes

## Quick start

```bash
# 1. Clone and copy env
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY and a random SCOUT_SECRET_KEY

# 2. Backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
playwright install chromium
uvicorn backend.main:app --reload

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 → register an account → upload your CV → click Search.

## Docker

```bash
cp .env.example .env   # fill in your keys
docker compose up --build
# open http://localhost:3000
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `SCOUT_SECRET_KEY` | Yes | Random string for signing auth tokens |
| `REED_API_KEY` | No | Improves Reed results (free at reed.co.uk/developers) |
| `ADZUNA_APP_ID` / `ADZUNA_API_KEY` | No | Adzuna API (free at developer.adzuna.com) |
| `DATABASE_URL` | No | Defaults to `sqlite+aiosqlite:///scout.db` |
| `SCOUT_CORS_ORIGINS` | No | Comma-separated allowed origins (defaults to localhost) |

## Notes on sources

Some job boards (LinkedIn, Indeed, Glassdoor) use anti-bot detection. Running from a residential IP and not hammering requests improves yield. Reed and Adzuna use proper APIs and are the most reliable sources.

Use the **Source Health** panel (click the log icon → Source Health tab) to see how many jobs each source returned after a search.

## License

MIT
