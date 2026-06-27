"""
core/database.py
SQLite database for tracking scraped jobs, scores, and application status.
Prevents the same job from being processed twice.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from core.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id          TEXT UNIQUE,          -- platform's own ID or URL hash
                title           TEXT NOT NULL,
                company         TEXT,
                location        TEXT,
                job_type        TEXT,
                salary_min      REAL,
                salary_max      REAL,
                currency        TEXT,
                description     TEXT,
                url             TEXT,
                source          TEXT,                 -- linkedin / indeed / glassdoor
                date_posted     TEXT,
                date_scraped    TEXT DEFAULT (datetime('now')),

                -- Scoring
                match_score     INTEGER DEFAULT NULL, -- 0-100
                match_reasons   TEXT DEFAULT NULL,    -- JSON list
                skill_gaps      TEXT DEFAULT NULL,    -- JSON list

                -- Processing
                status          TEXT DEFAULT 'new',
                -- new → scored → approved → tailored → applied → rejected

                -- Output files
                tailored_resume_path  TEXT,
                cover_letter_path     TEXT,
                outreach_email_draft  TEXT
            );

            CREATE TABLE IF NOT EXISTS run_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at      TEXT DEFAULT (datetime('now')),
                stage       TEXT,
                jobs_found  INTEGER DEFAULT 0,
                jobs_scored INTEGER DEFAULT 0,
                jobs_passed INTEGER DEFAULT 0,
                notes       TEXT
            );
        """)
    print("✅ Database ready:", DB_PATH)


def job_exists(job_id: str) -> bool:
    """Check if we've already seen this job (deduplication)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None


def get_job_by_id(job_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return dict(row) if row else None


def get_job_by_url(url: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE url = ? ORDER BY id DESC LIMIT 1", (url,)
        ).fetchone()
        return dict(row) if row else None


def upsert_job(job: dict) -> dict:
    """Insert a new job or refresh an existing one by job_id."""
    if job_exists(job["job_id"]):
        with get_connection() as conn:
            conn.execute("""
                UPDATE jobs SET
                    title = :title,
                    company = :company,
                    location = :location,
                    job_type = :job_type,
                    description = :description,
                    url = :url,
                    source = :source,
                    date_posted = :date_posted,
                    match_score = NULL,
                    match_reasons = NULL,
                    skill_gaps = NULL,
                    status = 'new',
                    tailored_resume_path = NULL,
                    cover_letter_path = NULL
                WHERE job_id = :job_id
            """, job)
    else:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs
                    (job_id, title, company, location, job_type,
                     salary_min, salary_max, currency, description, url, source, date_posted)
                VALUES
                    (:job_id, :title, :company, :location, :job_type,
                     :salary_min, :salary_max, :currency, :description, :url, :source, :date_posted)
            """, job)
    return get_job_by_id(job["job_id"])


def insert_job(job: dict) -> bool:
    """
    Insert a new job. Returns True if inserted, False if duplicate.
    job dict keys: job_id, title, company, location, job_type,
                   salary_min, salary_max, currency, description, url, source, date_posted
    """
    if job_exists(job["job_id"]):
        return False
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO jobs
                (job_id, title, company, location, job_type,
                 salary_min, salary_max, currency, description, url, source, date_posted)
            VALUES
                (:job_id, :title, :company, :location, :job_type,
                 :salary_min, :salary_max, :currency, :description, :url, :source, :date_posted)
        """, job)
    return True


def update_job_score(job_id: str, score: int, reasons: list, gaps: list, status: str = "scored"):
    with get_connection() as conn:
        conn.execute("""
            UPDATE jobs SET
                match_score   = ?,
                match_reasons = ?,
                skill_gaps    = ?,
                status        = ?
            WHERE job_id = ?
        """, (score, json.dumps(reasons), json.dumps(gaps), status, job_id))


def update_job_status(job_id: str, status: str, **kwargs):
    """Update any field on a job by job_id."""
    allowed = {
        "tailored_resume_path", "cover_letter_path",
        "outreach_email_draft", "status"
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    fields["status"] = status
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE job_id = ?", values)


def get_jobs_by_status(status: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY match_score DESC",
            (status,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_top_matches(min_score: int = 65, limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM jobs
            WHERE match_score >= ? AND status IN ('scored', 'approved')
            ORDER BY match_score DESC
            LIMIT ?
        """, (min_score, limit)).fetchall()
        return [dict(r) for r in rows]


def log_run(stage: str, jobs_found=0, jobs_scored=0, jobs_passed=0, notes=""):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO run_log (stage, jobs_found, jobs_scored, jobs_passed, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (stage, jobs_found, jobs_scored, jobs_passed, notes))
