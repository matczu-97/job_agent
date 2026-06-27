"""
agents/scout_agent.py
Stage 1 — Job Scout

Scrapes job listings from LinkedIn, Indeed, Glassdoor (and more)
using the free JobSpy library. Deduplicates against the local DB.
New jobs are saved with status='new' for the scorer to process.
"""

import hashlib
import re
from datetime import datetime

from rich.console import Console
from rich.table import Table

from core.config import (
    PROFILE, JOB_KEYWORDS, JOB_LOCATIONS, JOB_COUNTRY,
    JOB_SEARCH_DISTANCE_MILES, JOB_SITE_LIST, RESULTS_WANTED,
)
from core.database import insert_job, log_run, init_db

console = Console()


def _make_job_id(url: str, title: str, company: str) -> str:
    """Create a stable unique ID for a job listing."""
    raw = f"{url or ''}{title or ''}{company or ''}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _clean_text(text: str) -> str:
    if not text:
        return ""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', str(text)).strip()
    return text[:8000]  # Cap description length


def _is_excluded(title: str, profile: dict) -> bool:
    """Filter out jobs matching excluded keywords in the user's profile."""
    excluded = profile.get("preferences", {}).get("excluded_keywords", [])
    title_lower = (title or "").lower()
    return any(kw.lower() in title_lower for kw in excluded)


def run(keywords: list[str] = None, locations: list[str] = None, sites: list[str] = None) -> dict:
    """
    Run the job scout.
    Returns a summary dict: {found, inserted, skipped_duplicate, skipped_excluded}
    """
    try:
        from jobspy import scrape_jobs
    except ImportError:
        console.print("[red]❌ JobSpy not installed. Run: pip install python-jobspy[/red]")
        return {}

    keywords = keywords or JOB_KEYWORDS
    locations = locations or JOB_LOCATIONS
    sites = sites or JOB_SITE_LIST

    init_db()

    stats = {"found": 0, "inserted": 0, "skipped_duplicate": 0, "skipped_excluded": 0}
    all_new_jobs = []

    console.rule("[bold blue]🔍 Job Scout — Stage 1")
    console.print(
        f"[dim]Searching {len(locations)} location(s) in {JOB_COUNTRY} "
        f"(radius ~{JOB_SEARCH_DISTANCE_MILES} mi)[/dim]"
    )

    for keyword in keywords:
        for location in locations:
            console.print(f"\n[cyan]Searching:[/cyan] '{keyword}' in {location}")

            try:
                jobs_df = scrape_jobs(
                    site_name=sites,
                    search_term=keyword,
                    location=location,
                    distance=JOB_SEARCH_DISTANCE_MILES,
                    results_wanted=RESULTS_WANTED,
                    hours_old=48,
                    country_indeed=JOB_COUNTRY,
                )
            except Exception as e:
                console.print(f"[red]  Scrape error for '{keyword}' in {location}: {e}[/red]")
                continue

            if jobs_df is None or jobs_df.empty:
                console.print(f"  [yellow]No results for '{keyword}' in {location}[/yellow]")
                continue

            console.print(f"  Found [bold]{len(jobs_df)}[/bold] raw listings")
            stats["found"] += len(jobs_df)

            for _, row in jobs_df.iterrows():
                title = _clean_text(row.get("title", ""))
                company = _clean_text(row.get("company", ""))
                url = str(row.get("job_url", ""))

                if _is_excluded(title, PROFILE):
                    stats["skipped_excluded"] += 1
                    continue

                job_id = _make_job_id(url, title, company)

                job = {
                    "job_id":      job_id,
                    "title":       title,
                    "company":     company,
                    "location":    _clean_text(row.get("location", "")),
                    "job_type":    str(row.get("job_type", "")),
                    "salary_min":  _safe_float(row.get("min_amount")),
                    "salary_max":  _safe_float(row.get("max_amount")),
                    "currency":    str(row.get("currency", "ILS")),
                    "description": _clean_text(row.get("description", "")),
                    "url":         url,
                    "source":      str(row.get("site", "unknown")),
                    "date_posted": str(row.get("date_posted", "")),
                }

                inserted = insert_job(job)
                if inserted:
                    stats["inserted"] += 1
                    all_new_jobs.append(job)
                else:
                    stats["skipped_duplicate"] += 1

    # Print summary table
    _print_summary(stats, all_new_jobs)
    log_run("scout", jobs_found=stats["found"], notes=str(stats))

    return stats


def _safe_float(val) -> float | None:
    try:
        return float(val) if val and str(val) != "nan" else None
    except (ValueError, TypeError):
        return None


def _print_summary(stats: dict, new_jobs: list):
    console.print()
    console.rule("[bold green]Scout Complete")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Count", justify="right")
    table.add_row("Total found",         str(stats["found"]))
    table.add_row("✅ New (inserted)",    f"[green]{stats['inserted']}[/green]")
    table.add_row("⏭  Duplicates skipped", str(stats["skipped_duplicate"]))
    table.add_row("🚫 Excluded by filter", str(stats["skipped_excluded"]))
    console.print(table)

    if new_jobs:
        console.print("\n[bold]New jobs found:[/bold]")
        for j in new_jobs[:10]:
            console.print(f"  • [cyan]{j['title']}[/cyan] @ {j['company']} ({j['source']})")
        if len(new_jobs) > 10:
            console.print(f"  ... and {len(new_jobs) - 10} more")


if __name__ == "__main__":
    run()
