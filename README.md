# Scout

AI-powered personal job search platform. Scrapes multiple job boards, scores roles against your CV, surfaces relevant recruiters, and helps you apply — all triggered manually from a web dashboard.

## Stack
- **Backend** — Python 3.12 + FastAPI
- **Frontend** — React + Tailwind CSS
- **AI** — Claude API (`claude-sonnet-4-6`)
- **Scraping** — Playwright + httpx + BeautifulSoup
- **DB** — SQLite (dev) / PostgreSQL (prod)
- **Deploy** — Docker Compose

## Features
| Feature | Description |
|---|---|
| Job search | Scrapes LinkedIn, Indeed, Reed, Adzuna, Glassdoor, Totaljobs, CWJobs |
| Scoring | AI compatibility % — likelihood of interview based on your CV |
| Salary filter | Advertised salary or AI-estimated where not listed |
| Recruiter finder | LinkedIn recruiters/hiring managers at actively hiring companies |
| Tracker | Application status board + calendar |
| CV agent | Tailors your CV per role |
| Form agent | Assists with online application forms |

## Target Profile
- **Level:** Manager → Director
- **Function:** Consultancy, delivery, client services
- **Location:** Remote (global) · On-site/Hybrid in London
- **Salary:** £90k+ base
- **Industries:** All except gaming (deprioritised, not excluded)

## Quick Start
```bash
cp .env.example .env          # add API keys
docker compose up --build     # start everything
open http://localhost:3000    # open dashboard
```

## Environment
```
ANTHROPIC_API_KEY=
REED_API_KEY=
ADZUNA_APP_ID=
ADZUNA_API_KEY=
```
