"""
core/config.py
Loads all settings from .env and data/profile.json
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "outputs"))
OUTPUT_DIR.mkdir(exist_ok=True)

DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "jobs.db"))
MASTER_RESUME_PATH = DATA_DIR / "master_resume.docx"
PROFILE_PATH = DATA_DIR / "profile.json" 

# ── API Keys ────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
APIFY_API_KEY = os.getenv("APIFY_API_KEY")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
GMAIL_SENDER = os.getenv("GMAIL_SENDER")

# ── Job Search Settings ─────────────────────────────────────────────────
# Fallback when JOB_LOCATION is not set in .env — customize locations in .env instead
DEFAULT_JOB_LOCATIONS = ["Israel"]


def _parse_string_list(raw: str | None, default: list[str]) -> list[str]:
    """Parse a single value or JSON array from .env into a list of strings."""
    if not raw:
        return default
    raw = raw.strip()
    if raw.startswith("["):
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return [raw]


JOB_LOCATIONS = _parse_string_list(os.getenv("JOB_LOCATION"), DEFAULT_JOB_LOCATIONS)
JOB_COUNTRY = os.getenv("JOB_COUNTRY", "Israel")
JOB_RADIUS_KM = int(os.getenv("JOB_RADIUS_KM", 50))
JOB_SEARCH_DISTANCE_MILES = max(1, round(JOB_RADIUS_KM * 0.621371))
MIN_MATCH_SCORE = int(os.getenv("MIN_MATCH_SCORE", 65))
MAX_JOBS_PER_RUN = int(os.getenv("MAX_JOBS_PER_RUN", 20))
RESULTS_WANTED = int(os.getenv("RESULTS_WANTED", 50))

_raw_sites = os.getenv("JOB_SITE_LIST", '["linkedin","indeed","glassdoor"]')
JOB_SITE_LIST = json.loads(_raw_sites)

# ── User Profile ────────────────────────────────────────────────────────
def load_profile() -> dict:
    """Load user profile from data/profile.json"""
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(
            f"Profile not found at {PROFILE_PATH}. "
            "Copy data/profile.json and fill in your details."
        )
    with open(PROFILE_PATH) as f:
        return json.load(f)

PROFILE = load_profile()
JOB_KEYWORDS = PROFILE.get("job_search_keywords", ["Software Engineer"])

# ── Claude Model ────────────────────────────────────────────────────────
CLAUDE_MODEL = "claude-sonnet-4-6"
