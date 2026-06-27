"""
scheduler.py
Run the full job agent pipeline on a daily schedule.

Usage:
  python scheduler.py          # Runs daily at 8:00 AM
  python scheduler.py --now    # Run once immediately, then schedule
"""

import schedule
import time
import click
from rich.console import Console
from datetime import datetime

console = Console()


def run_pipeline(with_cover_letter: bool = False):
    console.rule(f"[bold cyan]Scheduled Run - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    from core.database import init_db
    from agents.scout_agent import run as scout
    from agents.scorer_agent import run as score
    from agents.tailor_agent import run as tailor

    init_db()
    scout()
    score()
    tailor()
    if with_cover_letter:
        from agents.cover_letter_agent import run as cover
        cover()
    console.print(f"\n[bold green]Daily run complete - {datetime.now().strftime('%H:%M')}[/bold green]")
    console.print("Next run tomorrow at 08:00. Press Ctrl+C to stop.\n")


@click.command()
@click.option("--now", is_flag=True, help="Run immediately before scheduling")
@click.option("--time", "run_time", default="08:00", help="Time to run daily (HH:MM)")
@click.option("--cover-letter", is_flag=True, help="Also write cover letters (off by default)")
def main(now, run_time, cover_letter):
    console.print(f"[bold cyan]📅 Job Agent Scheduler[/bold cyan]")
    console.print(f"   Daily run scheduled at [bold]{run_time}[/bold]")
    console.print("   Press Ctrl+C to stop\n")

    if now:
        run_pipeline(with_cover_letter=cover_letter)

    schedule.every().day.at(run_time).do(run_pipeline, with_cover_letter=cover_letter)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
