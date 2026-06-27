# 🤖 Job Agent System

An AI-powered job search agent that scans job boards, scores matches against your resume, tailors your resume per job, writes cover letters, and prepares outreach emails — all in Python.

## Architecture

```
job_agent/
├── agents/
│   ├── scout_agent.py        # Stage 1: Scrape & collect jobs
│   ├── scorer_agent.py       # Stage 2: Match & score jobs vs your profile
│   ├── tailor_agent.py       # Stage 3: Rewrite resume per job
│   ├── cover_letter_agent.py # Stage 4: Write cover letters
│   └── url_agent.py          # Single job URL: fetch, score, tailor
├── core/
│   ├── config.py             # Settings from .env + profile.json
│   ├── database.py           # SQLite job tracking
│   ├── job_fetcher.py        # Fetch job details from a posting URL
│   ├── llm.py                # Claude API wrapper
│   └── resume_parser.py      # Parse .docx / PDF resumes
├── data/
│   ├── master_resume.docx    # Your master resume (put it here)
│   └── profile.json          # Skills, preferences, job keywords
├── outputs/                  # Tailored resumes & cover letters
├── main.py                   # CLI entry point
├── scheduler.py              # Run daily automatically
├── requirements.txt
└── .env.example
```

## Stages

| Stage | Agent | What it does |
|-------|-------|-------------|
| 1 | Scout | Scrapes LinkedIn, Indeed, Glassdoor by keyword across multiple locations |
| 2 | Scorer | AI scores each job 0–100 vs your resume |
| 3 | Tailor | Rewrites your resume for each high-scoring job |
| 4 | Cover Letter | Writes personalized cover letter per job (**opt-in only**) |
| URL | URL Agent | Paste one job link → fetch, score, and tailor resume |

> Stage 5 (Apply / Google Sheets outreach) is planned but not implemented yet.

## Quick Start

```bash
# 1. Clone / copy this project
cd job_agent

# 2. Create a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\pip install -r requirements.txt
# macOS/Linux:
# source .venv/bin/activate && pip install -r requirements.txt

# 3. Copy and fill in your config
cp .env.example .env        # Windows: copy .env.example .env
# Edit .env with your API keys and job search settings

# 4. Add your resume
# Copy your .docx resume to data/master_resume.docx

# 5. Edit your profile
# Edit data/profile.json with your skills and job preferences

# 6. Run Stage 1 only (job scout)
python main.py --stage 1

# 7. Run scout, score, and tailor (default pipeline — no cover letter)
python main.py --stage all

# 8. View tracked jobs
python main.py --status

# 9. Process a specific job link (score + tailored resume)
python main.py --url "https://www.linkedin.com/jobs/view/1234567890"

# 10. Add a cover letter when you need one
python main.py --url "https://..." --cover-letter
python main.py --stage 4
python main.py --stage all --cover-letter

# 11. Run on a daily schedule
python scheduler.py
```

## Single Job URL

Paste a link to any job posting (LinkedIn, Indeed, Glassdoor, etc.):

```bash
python main.py --url "https://www.linkedin.com/jobs/view/1234567890"
```

This will:
1. Fetch the job title, company, and description from the URL
2. Score it against your resume (0–100 with match reasons and skill gaps)
3. Save a tailored resume to `outputs/resumes/`
4. Track the job in the local SQLite database

> **LinkedIn note:** Some URLs require a public posting or may redirect to login. Indeed/Glassdoor links tend to work more reliably.

## Job Search Settings (`.env`)

| Variable | Description |
|----------|-------------|
| `JOB_LOCATION` | One place (`Israel`) or a JSON list of cities to search |
| `JOB_COUNTRY` | Country for Indeed/Glassdoor (default: `Israel`) |
| `JOB_RADIUS_KM` | Search radius around each location |
| `JOB_SITE_LIST` | Boards to scrape: `linkedin`, `indeed`, `glassdoor` |
| `MIN_MATCH_SCORE` | Only auto-approve jobs scoring above this (0–100) |
| `RESULTS_WANTED` | Max listings fetched per keyword × location |

Job keywords come from `data/profile.json` → `job_search_keywords`.

Example — search all of Israel:

```env
JOB_LOCATION=["Israel", "Tel Aviv, Israel", "Haifa, Israel", "Jerusalem, Israel"]
JOB_COUNTRY=Israel
JOB_RADIUS_KM=200
```

## API Keys

| Key | Where to get it | Cost |
|-----|----------------|------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | ~$0.01/run |

> **Note:** JobSpy is used for scraping (free, no key needed).

## CLI Reference

```bash
python main.py --stage 1          # Scout only
python main.py --stage 2          # Score only
python main.py --stage 3          # Tailor only
python main.py --stage 4          # Cover letters only (explicit)
python main.py --stage all        # Scout + score + tailor (no cover letter)
python main.py --cover-letter     # Also write cover letters for tailored jobs
python main.py --status           # Job tracker dashboard
python main.py --url <job_url>    # Score + tailor one job
python main.py --url <job_url> --cover-letter  # Also write cover letter
python main.py --no-tailor        # With --url: score only
python main.py --min-score 70     # Override match threshold
```
