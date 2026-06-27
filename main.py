"""
main.py
Job Agent System — Main Entry Point

Run individual stages or the full pipeline.

Usage:
  python main.py --stage 1          # Scout only
  python main.py --stage 2          # Score only
  python main.py --stage 3          # Tailor only
  python main.py --stage all        # Run scout, score, tailor (no cover letter)
  python main.py --stage 4          # Cover letters only (explicit)
  python main.py --cover-letter      # Add cover letters to the run
  python main.py --status           # Show job tracker
  python main.py --url <job_url>    # Score + tailor one job from a link
  python main.py --url <job_url> --cover-letter  # Also write a cover letter
"""

import click
from rich.console import Console
from rich.table import Table
from rich import box
from core.database import init_db, get_jobs_by_status, get_top_matches

console = Console()


def print_banner():
    console.print("""
[bold cyan]
  ╔══════════════════════════════════╗
  ║    🤖  JOB AGENT SYSTEM          ║
  ║    AI-Powered Job Search         ║
  ╚══════════════════════════════════╝
[/bold cyan]""")


@click.command()
@click.option("--stage", default="1", help="Stage to run: 1, 2, 3, 4, or 'all'")
@click.option("--status", is_flag=True, help="Show job tracker dashboard")
@click.option("--min-score", default=None, type=int, help="Override minimum match score")
@click.option("--url", default=None, help="Process a specific job URL (score + tailor resume)")
@click.option("--no-tailor", is_flag=True, help="With --url, score only — skip resume tailoring")
@click.option("--cover-letter", is_flag=True, help="Also write cover letters (off by default)")
def main(stage, status, min_score, url, no_tailor, cover_letter):

    print_banner()
    init_db()

    if url:
        from agents.url_agent import run as process_url
        process_url(
            url,
            min_score=min_score,
            skip_tailor=no_tailor,
            with_cover_letter=cover_letter,
        )
        return

    if status:
        show_status()
        return

    if stage == "1" or stage == "all":
        console.print("\n[bold]▶ Stage 1: Scouting jobs...[/bold]")
        from agents.scout_agent import run as scout
        scout()

    if stage == "2" or stage == "all":
        console.print("\n[bold]▶ Stage 2: Scoring matches...[/bold]")
        from agents.scorer_agent import run as score
        score(min_score=min_score)

    if stage == "3" or stage == "all":
        console.print("\n[bold]▶ Stage 3: Tailoring resumes...[/bold]")
        from agents.tailor_agent import run as tailor
        tailor()

    if stage == "4" or cover_letter:
        console.print("\n[bold]▶ Stage 4: Writing cover letters...[/bold]")
        from agents.cover_letter_agent import run as cover
        cover()

    if stage == "all":
        console.print("\n[bold green]✅ Pipeline complete![/bold green]")
        show_status()


def show_status():
    """Print a summary dashboard of all tracked jobs."""
    console.rule("[bold cyan]📊 Job Tracker Dashboard")

    top = get_top_matches(min_score=0, limit=30)
    if not top:
        console.print("[yellow]No jobs tracked yet. Run: python main.py --stage 1[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Score", width=6, justify="center")
    table.add_column("Title", width=35)
    table.add_column("Company", width=22)
    table.add_column("Source", width=10)
    table.add_column("Status", width=12)

    status_colors = {
        "new": "white", "scored": "yellow", "approved": "cyan",
        "tailored": "blue", "ready": "green", "applied": "bold green",
        "rejected": "red"
    }

    for i, job in enumerate(top, 1):
        score = job["match_score"] or 0
        score_color = "green" if score >= 70 else "yellow" if score >= 50 else "red"
        status = job["status"]
        status_color = status_colors.get(status, "white")

        table.add_row(
            str(i),
            f"[{score_color}]{score}[/{score_color}]",
            (job["title"] or "")[:35],
            (job["company"] or "")[:22],
            (job["source"] or "")[:10],
            f"[{status_color}]{status}[/{status_color}]",
        )

    console.print(table)

    # Counts by status
    statuses = ["new", "scored", "approved", "tailored", "ready", "applied"]
    console.print("\n[bold]Status breakdown:[/bold]")
    for s in statuses:
        jobs = get_jobs_by_status(s)
        if jobs:
            console.print(f"  {s:<12} {len(jobs)}")


if __name__ == "__main__":
    main()
