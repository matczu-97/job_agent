"""
agents/scorer_agent.py
Stage 2 — Match Scorer

Uses Claude to score each new job (0-100) against your resume/profile.
Only jobs scoring above MIN_MATCH_SCORE are passed forward to the tailor.
"""

import json
from rich.console import Console
from rich.progress import track

from core.config import PROFILE, MIN_MATCH_SCORE
from core.database import get_jobs_by_status, update_job_score, log_run
from core.resume_parser import load_resume_text
from core.llm import ask

console = Console()

SCORER_SYSTEM = """You are an expert technical recruiter who evaluates job-candidate fit.
You analyze job descriptions and candidate resumes objectively.
You always respond in valid JSON only."""

SCORER_PROMPT = """
Analyze how well this candidate matches this job posting.

## CANDIDATE PROFILE
{resume_text}

## JOB POSTING
Title: {title}
Company: {company}
Location: {location}
Description:
{description}

## YOUR TASK
Return a JSON object with exactly these fields:
{{
  "score": <integer 0-100>,
  "match_reasons": [<3-5 specific reasons this is a good match, be concrete>],
  "skill_gaps": [<specific skills/experience the job requires that the candidate lacks>],
  "verdict": "<one of: strong_match | good_match | weak_match | poor_match>",
  "one_line": "<one sentence summary of fit>"
}}

Scoring guide:
- 85-100: Nearly perfect match, apply immediately
- 70-84:  Good match, worth tailoring resume
- 55-69:  Partial match, notable gaps
- 0-54:   Poor match, skip

Be strict. A score of 80+ means the candidate could get an interview without any changes.
"""


def score_job(job: dict, resume_text: str) -> dict:
    """Score a single job. Returns the parsed JSON result from Claude."""
    prompt = SCORER_PROMPT.format(
        resume_text=resume_text[:3000],  # Cap to save tokens
        title=job["title"],
        company=job["company"] or "Unknown",
        location=job["location"] or "Unknown",
        description=(job["description"] or "")[:3000],
    )

    try:
        result = ask(prompt, system=SCORER_SYSTEM, max_tokens=800, json_mode=True)
        return result
    except Exception as e:
        console.print(f"[red]  Scoring error: {e}[/red]")
        return {
            "score": 0,
            "match_reasons": [],
            "skill_gaps": ["Error during scoring"],
            "verdict": "poor_match",
            "one_line": "Scoring failed"
        }


def run(min_score: int = None) -> dict:
    """
    Score all jobs with status='new'.
    Jobs above min_score are updated to status='approved'.
    Jobs below are updated to status='scored' (for review).
    """
    min_score = min_score or MIN_MATCH_SCORE

    console.rule("[bold blue]🧠 Match Scorer — Stage 2")

    new_jobs = get_jobs_by_status("new")
    if not new_jobs:
        console.print("[yellow]No new jobs to score. Run the scout first.[/yellow]")
        return {"scored": 0, "approved": 0, "rejected": 0}

    console.print(f"Scoring [bold]{len(new_jobs)}[/bold] jobs against your resume...\n")

    resume_text = load_resume_text()
    stats = {"scored": 0, "approved": 0, "rejected": 0}

    for job in track(new_jobs, description="Scoring..."):
        result = score_job(job, resume_text)
        score = result.get("score", 0)
        reasons = result.get("match_reasons", [])
        gaps = result.get("skill_gaps", [])
        status = "approved" if score >= min_score else "scored"

        update_job_score(job["job_id"], score, reasons, gaps, status)
        stats["scored"] += 1
        if status == "approved":
            stats["approved"] += 1
        else:
            stats["rejected"] += 1

        # Print each result
        color = "green" if score >= min_score else "yellow" if score >= 50 else "red"
        verdict = result.get("verdict", "")
        one_line = result.get("one_line", "")
        console.print(
            f"  [{color}]{score:3d}[/{color}] {job['title'][:45]:<45} "
            f"@ {(job['company'] or 'N/A')[:25]:<25} — {one_line[:60]}"
        )

    _print_summary(stats, min_score)
    log_run("scorer", jobs_scored=stats["scored"], jobs_passed=stats["approved"])
    return stats


def _print_summary(stats: dict, min_score: int):
    console.print()
    console.rule("[bold green]Scoring Complete")
    console.print(f"  Scored:           [bold]{stats['scored']}[/bold]")
    console.print(f"  ✅ Approved (≥{min_score}): [bold green]{stats['approved']}[/bold green]")
    console.print(f"  ❌ Below threshold: [dim]{stats['rejected']}[/dim]")
    console.print()
    console.print("Run [bold cyan]python main.py --stage 3[/bold cyan] to tailor resumes for approved jobs.")


if __name__ == "__main__":
    run()
