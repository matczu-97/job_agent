"""
agents/url_agent.py
Process a single job URL: fetch posting, score match, tailor resume.
"""

import json

from rich.console import Console
from rich.panel import Panel

from core.config import MIN_MATCH_SCORE
from core.database import init_db, upsert_job, update_job_score, update_job_status, log_run
from core.job_fetcher import fetch_job_from_url, normalize_url
from core.resume_parser import load_resume_text
from agents.scorer_agent import score_job
from agents.tailor_agent import tailor_job

console = Console()


def _print_score_result(job: dict, result: dict, min_score: int):
    score = result.get("score", 0)
    color = "green" if score >= min_score else "yellow" if score >= 50 else "red"

    console.print()
    console.print(Panel.fit(
        f"[bold]{job['title']}[/bold]\n"
        f"{job['company'] or 'Unknown company'} · {job['location'] or 'Unknown location'}\n"
        f"[{color}]Score: {score}/100[/{color}] · {result.get('verdict', '')}\n"
        f"{result.get('one_line', '')}",
        title="Match Score",
        border_style=color,
    ))

    reasons = result.get("match_reasons") or []
    gaps = result.get("skill_gaps") or []

    if reasons:
        console.print("\n[bold green]Why it's a match[/bold green]")
        for reason in reasons:
            console.print(f"  • {reason}")

    if gaps:
        console.print("\n[bold yellow]Skill gaps[/bold yellow]")
        for gap in gaps:
            console.print(f"  • {gap}")


def run(
    url: str,
    min_score: int = None,
    skip_tailor: bool = False,
    with_cover_letter: bool = False,
) -> dict:
    """
    Fetch a job from URL, score it, and tailor a resume.
    Cover letter is written only when with_cover_letter=True.
    """
    min_score = min_score if min_score is not None else MIN_MATCH_SCORE
    url = normalize_url(url)

    console.rule("[bold blue]🔗 Single Job URL — Score & Tailor")
    console.print(f"URL: [cyan]{url}[/cyan]\n")

    init_db()

    console.print("[dim]Fetching job posting...[/dim]")
    try:
        job_data = fetch_job_from_url(url)
    except Exception as e:
        console.print(f"[red]❌ Failed to fetch job: {e}[/red]")
        return {"success": False, "error": str(e)}

    job = upsert_job(job_data)
    console.print(
        f"[green]✓[/green] Loaded: [bold]{job['title']}[/bold] @ {job['company'] or 'Unknown'}"
    )

    resume_text = load_resume_text()
    console.print("[dim]Scoring against your resume...[/dim]")
    result = score_job(job, resume_text)
    score = result.get("score", 0)
    status = "approved" if score >= min_score else "scored"

    update_job_score(
        job["job_id"],
        score,
        result.get("match_reasons") or [],
        result.get("skill_gaps") or [],
        status,
    )
    job = {**job, "match_score": score, "status": status}

    _print_score_result(job, result, min_score)

    stats = {"success": True, "score": score, "resume_path": None, "cover_letter_path": None}

    if skip_tailor:
        console.print("\n[yellow]Skipped resume tailoring (--no-tailor).[/yellow]")
        if with_cover_letter:
            console.print("[yellow]Skipped cover letter too (requires tailored resume).[/yellow]")
        log_run("url", jobs_scored=1, jobs_passed=1 if score >= min_score else 0, notes=url)
        return stats

    console.print("\n[dim]Tailoring resume for this job...[/dim]")
    try:
        out_path = tailor_job(job, resume_text=resume_text)
        stats["resume_path"] = str(out_path)
        console.print(f"\n[bold green]✅ Tailored resume saved:[/bold green] [cyan]{out_path}[/cyan]")
    except Exception as e:
        console.print(f"[red]❌ Tailoring failed: {e}[/red]")
        stats["success"] = False
        stats["error"] = str(e)
        log_run(
            "url",
            jobs_scored=1,
            jobs_passed=1 if score >= min_score else 0,
            notes=json.dumps({"url": url, "score": score, "error": str(e)}),
        )
        return stats

    if with_cover_letter:
        console.print("\n[dim]Writing cover letter...[/dim]")
        try:
            from agents.cover_letter_agent import write_cover_letter, save_cover_letter
            letter_text = write_cover_letter(job, resume_text)
            letter_path = save_cover_letter(letter_text, job)
            update_job_status(
                job["job_id"],
                status="ready",
                cover_letter_path=str(letter_path),
            )
            stats["cover_letter_path"] = str(letter_path)
            console.print(f"[bold green]✅ Cover letter saved:[/bold green] [cyan]{letter_path}[/cyan]")
        except Exception as e:
            console.print(f"[red]❌ Cover letter failed: {e}[/red]")
            stats["cover_letter_error"] = str(e)

    log_run(
        "url",
        jobs_scored=1,
        jobs_passed=1 if score >= min_score else 0,
        notes=json.dumps({
            "url": url,
            "score": score,
            "resume": stats.get("resume_path"),
            "cover_letter": stats.get("cover_letter_path"),
        }),
    )
    return stats


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        console.print("Usage: python agents/url_agent.py <job_url>")
        raise SystemExit(1)
    run(sys.argv[1])
