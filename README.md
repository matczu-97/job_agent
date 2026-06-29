# Job Agent System

An AI-powered job search pipeline in Python. It scrapes job boards, scores listings against your resume with Claude, tailors a `.docx` resume per role, and optionally writes cover letters — all tracked in a local SQLite database.

**You bring your own Claude API key.** Stages 2–4 and the URL workflow call the [Anthropic API](https://docs.anthropic.com/) directly. This project does **not** use the Cursor API or any IDE integration.

---

## Features

- **Scout** — Scrape LinkedIn, Indeed, and Glassdoor via [JobSpy](https://github.com/speedyapply/JobSpy) (free, no API key)
- **Score** — Claude compares each job to your profile and assigns a 0–100 match score
- **Tailor** — Claude rewrites your master resume into a one-page, job-specific `.docx`
- **Cover letter** — Optional personalized cover letters (opt-in only)
- **URL mode** — Paste a single job link to fetch, score, and tailor without running a full scout
- **Tracker** — SQLite dashboard of all jobs, scores, and statuses

---

## How it works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Stage 1    │     │  Stage 2    │     │  Stage 3    │     │  Stage 4     │
│  Scout      │ ──► │  Scorer     │ ──► │  Tailor     │     │  Cover Letter│
│  (JobSpy)   │     │  (Claude)   │     │  (Claude)   │     │  (Claude)    │
└─────────────┘     └─────────────┘     └─────────────┘     └──────────────┘
                                              ▲                    ▲
                                              │                    │
                                    score ≥ MIN_MATCH_SCORE   opt-in only
                                    (default: 70)

Alternative path:

  python main.py --url "<job_url>"  →  fetch → score → tailor  (→ cover letter with --cover-letter)
```

| Stage | Agent | API needed | What it does |
|-------|-------|------------|--------------|
| 1 | Scout | None | Scrapes job boards by keyword × location |
| 2 | Scorer | **Claude** | Scores each job 0–100 vs your resume |
| 3 | Tailor | **Claude** | Rewrites resume for approved jobs |
| 4 | Cover Letter | **Claude** | Writes a cover letter per tailored job (**opt-in only**) |
| URL | URL Agent | **Claude** | Fetch one posting → score → tailor |

> Stage 5 (auto-apply / Google Sheets outreach) is planned but not implemented.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Python 3.10+** | Uses modern type hints (`str \| None`, etc.) |
| **Anthropic API key** | **Required** for scoring, tailoring, and cover letters |
| **Your resume** | A `.docx` file placed at `data/master_resume.docx` |

Job scraping uses JobSpy and does **not** require a separate scraping API key.

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/matczu-97/job_agent.git
cd job_agent

python -m venv .venv

# Windows
.venv\Scripts\activate
.venv\Scripts\pip install -r requirements.txt

# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Add your Claude API key (required)

1. Create an account at [console.anthropic.com](https://console.anthropic.com).
2. Go to **API Keys** and create a key (starts with `sk-ant-...`).
3. Copy the example env file and open it:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

4. Set your key in `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

> **Important:** Never commit `.env` to git. It is listed in `.gitignore`. If you publish a fork, rotate any key that was ever committed.

Without a valid `ANTHROPIC_API_KEY`, Stage 1 (scout) may still run, but scoring, tailoring, cover letters, and `--url` will fail when they call Claude.

### 3. Add your resume and profile

Your personal files stay local — they are **not** committed to git.

```bash
# Windows — copy the profile template
copy data\profile.example.json data\profile.json

# macOS / Linux
cp data/profile.example.json data/profile.json
```

Then:

1. Edit `data/profile.json` with your contact info, skills, experience, and `job_search_keywords`.
2. Copy your master resume to `data/master_resume.docx` (or `data/master_resume.pdf`).

At minimum, fill in `job_search_keywords` — these drive what jobs the scout searches for.

### 4. Run the pipeline

```bash
# Scout only — find jobs (no Claude calls)
python main.py --stage 1

# Full pipeline: scout → score → tailor (no cover letter)
python main.py --stage all

# View tracked jobs
python main.py --status
```

---

## Configuration

### Environment variables (`.env`)

Copy `.env.example` → `.env` and edit. Only `ANTHROPIC_API_KEY` is strictly required for AI stages.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | **Yes** (for AI stages) | — | Your Claude API key from [console.anthropic.com](https://console.anthropic.com) |
| `JOB_LOCATION` | No | `["Israel"]` | One place or a JSON array of cities/regions to search |
| `JOB_COUNTRY` | No | `Israel` | Country for Indeed/Glassdoor |
| `JOB_RADIUS_KM` | No | `50` | Search radius around each location |
| `JOB_SITE_LIST` | No | `["linkedin","indeed","glassdoor"]` | Job boards to scrape |
| `MIN_MATCH_SCORE` | No | `70` | Jobs scoring at or above this are approved for tailoring |
| `MAX_JOBS_PER_RUN` | No | `20` | Cap on jobs processed per scout run |
| `RESULTS_WANTED` | No | `50` | Listings fetched per keyword × location before filtering |
| `OUTPUT_DIR` | No | `./outputs` | Tailored resumes and cover letters |
| `DB_PATH` | No | `./data/jobs.db` | SQLite database path |
| `GOOGLE_CREDENTIALS_PATH` | No | — | Optional; for future Sheets/Drive integration |
| `GMAIL_SENDER` | No | — | Optional; for future outreach drafts |

**Keywords** come from `data/profile.json` → `job_search_keywords`, not from `.env`.

Example — search across Israel:

```env
JOB_LOCATION=["Israel", "Tel Aviv, Israel", "Haifa, Israel", "Jerusalem, Israel"]
JOB_COUNTRY=Israel
JOB_RADIUS_KM=200
MIN_MATCH_SCORE=70
```

### Profile (`data/profile.json`)

Copy `data/profile.example.json` → `data/profile.json` and customize. The example file is tracked in git; your personal `profile.json` is gitignored.

Important fields:

| Field | Purpose |
|-------|---------|
| `name`, `email`, `phone`, `location` | Contact block on tailored resumes |
| `summary`, `skills`, `experience`, `projects`, `education` | Used by Claude for scoring and tailoring |
| `preferences.excluded_keywords` | Jobs containing these terms are deprioritized |
| `job_search_keywords` | Search terms used by the scout agent |

---

## Usage

### CLI reference

```bash
python main.py --stage 1              # Scout only
python main.py --stage 2              # Score unscored jobs
python main.py --stage 3              # Tailor approved jobs
python main.py --stage 4              # Cover letters only (explicit)
python main.py --stage all            # Scout + score + tailor (no cover letter)
python main.py --cover-letter         # Also write cover letters in this run
python main.py --status               # Job tracker dashboard
python main.py --url <job_url>        # Fetch, score, and tailor one job
python main.py --url <job_url> --cover-letter   # Also write a cover letter
python main.py --url <job_url> --no-tailor      # Score only, skip tailoring
python main.py --min-score 75         # Override match threshold for this run
```

**Cover letters are opt-in.** `--stage all` does not write them unless you also pass `--cover-letter` or run `--stage 4`.

### Single job URL

Paste a link to a specific posting:

```bash
python main.py --url "https://www.linkedin.com/jobs/view/1234567890"
```

This will:

1. Fetch title, company, and description from the URL
2. Score the job against your resume (0–100, with match reasons and skill gaps)
3. Save a tailored resume to `outputs/resumes/`
4. Record the job in the local SQLite database

**LinkedIn tip:** Direct job view URLs (`/jobs/view/<id>`) work best. Search-result or login-walled URLs often fail. Indeed and Glassdoor links tend to be more reliable.

### Daily scheduler

```bash
python scheduler.py              # Run daily at 08:00
python scheduler.py --now        # Run once immediately, then schedule
python scheduler.py --time 09:30 # Custom time
python scheduler.py --cover-letter   # Include cover letters in scheduled runs
```

---

## Project layout

```
job_agent/
├── agents/
│   ├── scout_agent.py         # Stage 1: scrape jobs (JobSpy)
│   ├── scorer_agent.py        # Stage 2: Claude scoring
│   ├── tailor_agent.py        # Stage 3: Claude + docx tailoring
│   ├── cover_letter_agent.py  # Stage 4: cover letters (opt-in)
│   └── url_agent.py           # Single URL: fetch → score → tailor
├── core/
│   ├── config.py              # Loads .env + profile.json
│   ├── database.py            # SQLite job tracking
│   ├── job_fetcher.py         # Fetch job details from a posting URL
│   ├── llm.py                 # Anthropic SDK wrapper (claude-sonnet-4-6)
│   ├── resume_parser.py       # Parse .docx / PDF resumes
│   └── text_utils.py          # Sanitize AI output for Word documents
├── data/
│   ├── profile.example.json   # Template — copy to profile.json
│   ├── profile.json           # Your profile (gitignored — you create this)
│   ├── master_resume.docx     # Your master resume (gitignored — you add this)
│   └── jobs.db                # Local tracker (gitignored after first run)
├── outputs/                   # Tailored resumes & cover letters (gitignored)
├── main.py                    # CLI entry point
├── scheduler.py               # Daily automation
├── requirements.txt
├── LICENSE                    # MIT License
└── .env.example               # Template — copy to .env and fill in your key
```

---

## Outputs

| Path | Contents |
|------|----------|
| `outputs/resumes/` | Tailored `.docx` resumes, one per job |
| `outputs/cover_letters/` | Cover letters (when `--cover-letter` or `--stage 4` is used) |
| `data/jobs.db` | SQLite database of all scraped and processed jobs |

---

## API costs

| Service | Key required | Typical cost |
|---------|--------------|--------------|
| **Anthropic (Claude)** | `ANTHROPIC_API_KEY` | Roughly ~$0.01–0.05 per job scored/tailored (varies by description length) |
| **JobSpy** | None | Free |

Billing is on your Anthropic account. Monitor usage at [console.anthropic.com](https://console.anthropic.com).

---

## Security and privacy

- **`.env` is gitignored** — keep your API key local only.
- **`data/profile.json` and `data/master_resume.*` are gitignored** — your personal data stays on your machine.
- **`outputs/` and `data/jobs.db` are gitignored** — tailored documents and job history are not pushed to the repo.
- Resume and profile data are sent to Anthropic when you run scoring, tailoring, or cover-letter stages. Review [Anthropic's data policies](https://www.anthropic.com/privacy) before use.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| Auth / 401 errors from Claude | Missing or invalid API key | Set `ANTHROPIC_API_KEY` in `.env` |
| Scout finds no jobs | Keywords or locations too narrow | Edit `job_search_keywords` in `profile.json` and `JOB_LOCATION` in `.env` |
| URL fetch fails on LinkedIn | Login wall or search-results URL | Use a direct `/jobs/view/<id>` link or try Indeed |
| No jobs tailored | Scores below threshold | Lower `MIN_MATCH_SCORE` or use `--min-score` |
| `Profile not found` | Missing `data/profile.json` | `cp data/profile.example.json data/profile.json` and edit |

---

## License

This project is licensed under the [MIT License](LICENSE).

You are free to use, modify, and distribute the code. Keep the copyright notice in copies you share. There is no warranty — use at your own risk.
