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
# 1. Clone
git clone https://github.com/emoggio/JobSearcher.git
cd JobSearcher
cp .env.example .env
```

**Edit `.env`** — two things are required:

```env
# Get your key at console.anthropic.com → API Keys
ANTHROPIC_API_KEY=sk-ant-api03-your-real-key-here

# Generate any random string, e.g.: python -c "import secrets; print(secrets.token_hex(32))"
SCOUT_SECRET_KEY=any-long-random-string-here
```

> **Using Claude Code / a company gateway?**
> If you're running Claude Code CLI in the same terminal, your company token is already active.
> Run this once to copy it automatically into `.env`:
> ```bash
> python -c "
> import json, os, re
> cfg = json.load(open(os.path.expanduser('~/.claude/config.json')))
> key = cfg.get('primaryApiKey', '')
> base = os.getenv('ANTHROPIC_BASE_URL', '')
> headers = os.getenv('ANTHROPIC_CUSTOM_HEADERS', '')
> env = open('.env').read()
> env = re.sub(r'ANTHROPIC_API_KEY=.*', f'ANTHROPIC_API_KEY={key}', env)
> if base:
>     env = re.sub(r'ANTHROPIC_BASE_URL=.*', f'ANTHROPIC_BASE_URL={base}', env) if 'ANTHROPIC_BASE_URL=' in env else env + f'\nANTHROPIC_BASE_URL={base}'
> if headers:
>     env = env + f'\nANTHROPIC_CUSTOM_HEADERS={headers}' if 'ANTHROPIC_CUSTOM_HEADERS=' not in env else re.sub(r'ANTHROPIC_CUSTOM_HEADERS=.*', f'ANTHROPIC_CUSTOM_HEADERS={headers}', env)
> open('.env', 'w').write(env)
> print('Done')
> "
> ```

```bash
# 2. Backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
playwright install chromium
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** → register an account → upload your CV → click Search.

> **On your phone / another device on the same WiFi?**
> Find your PC's local IP (`ipconfig` on Windows, `ifconfig` on Mac/Linux) and open
> `http://<your-ip>:3000` on your phone. Make sure the backend runs with `--host 0.0.0.0`.

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
