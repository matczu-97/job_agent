"""
core/job_fetcher.py
Fetch job details from a specific posting URL.
"""

import hashlib
import re
from urllib.parse import urlparse

import httpx

from core.llm import ask

FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

EXTRACT_SYSTEM = (
    "You extract structured job posting data from web pages. "
    "Return factual content only — do not invent details. JSON only."
)

EXTRACT_PROMPT = """
Extract job posting details from this URL and page content.

URL: {url}
Detected source: {source}

Page text (may be truncated):
{page_text}

Return a JSON object with exactly these fields:
{{
  "title": "<job title>",
  "company": "<company name>",
  "location": "<job location or Unknown>",
  "description": "<full job description as plain text>",
  "job_type": "<fulltime|parttime|contract|internship or empty string>"
}}

If the page is a login wall, use any visible job info. description should be as complete as possible.
"""


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


def make_job_id(url: str) -> str:
    return hashlib.md5(normalize_url(url).lower().encode()).hexdigest()[:16]


def detect_source(url: str) -> str:
    host = urlparse(normalize_url(url)).netloc.lower()
    if "linkedin" in host:
        return "linkedin"
    if "indeed" in host:
        return "indeed"
    if "glassdoor" in host:
        return "glassdoor"
    if "ziprecruiter" in host:
        return "ziprecruiter"
    return "url"


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _fetch_page_text(url: str) -> str:
    response = httpx.get(
        normalize_url(url),
        headers=FETCH_HEADERS,
        follow_redirects=True,
        timeout=30,
    )
    response.raise_for_status()
    if "signup" in str(response.url).lower() and "linkedin" in url.lower():
        raise ValueError(
            "LinkedIn redirected to login. Open the job in your browser while logged in, "
            "or copy the full public job URL."
        )
    return html_to_text(response.text)


def _fetch_linkedin_description(url: str) -> str | None:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None

    response = httpx.get(
        normalize_url(url),
        headers=FETCH_HEADERS,
        follow_redirects=True,
        timeout=30,
    )
    response.raise_for_status()
    if "signup" in str(response.url).lower():
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    markup = soup.find("div", class_=lambda x: x and "show-more-less-html__markup" in x)
    if markup:
        return markup.get_text(separator="\n", strip=True)
    return None


def _extract_with_llm(url: str, source: str, page_text: str) -> dict:
    result = ask(
        EXTRACT_PROMPT.format(
            url=url,
            source=source,
            page_text=page_text[:12000],
        ),
        system=EXTRACT_SYSTEM,
        max_tokens=2500,
        json_mode=True,
    )
    return result


def fetch_job_from_url(url: str) -> dict:
    """
    Fetch a job posting from a URL and return a job dict ready for the database.
    """
    url = normalize_url(url)
    source = detect_source(url)

    page_text = _fetch_page_text(url)
    if not page_text:
        raise ValueError("Could not read any content from the job URL.")

    description = None
    if source == "linkedin":
        description = _fetch_linkedin_description(url)

    extracted = _extract_with_llm(url, source, page_text)
    if description and len(description) > len(extracted.get("description") or ""):
        extracted["description"] = description

    title = (extracted.get("title") or "").strip()
    company = (extracted.get("company") or "").strip()
    description = (extracted.get("description") or page_text[:8000]).strip()

    if not title:
        raise ValueError("Could not determine the job title from this URL.")

    return {
        "job_id": make_job_id(url),
        "title": title,
        "company": company or None,
        "location": (extracted.get("location") or "Unknown").strip(),
        "job_type": (extracted.get("job_type") or "").strip() or None,
        "salary_min": None,
        "salary_max": None,
        "currency": "ILS",
        "description": description,
        "url": url,
        "source": source,
        "date_posted": None,
    }
