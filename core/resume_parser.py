"""
core/resume_parser.py
Parse .docx or PDF resume into clean text for the AI agents.
"""

import json
from pathlib import Path
from core.config import MASTER_RESUME_PATH, PROFILE


def parse_docx(path: Path) -> str:
    """Extract all text from a .docx file."""
    from docx import Document
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def parse_pdf(path: Path) -> str:
    """Extract all text from a PDF file."""
    import PyPDF2
    text = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text.append(page.extract_text() or "")
    return "\n".join(text)


def load_resume_text(path: Path = None) -> str:
    """
    Load resume from data/master_resume.docx (or PDF).
    Falls back to building a text summary from profile.json if no file exists.
    """
    target = path or MASTER_RESUME_PATH

    if target.exists():
        suffix = target.suffix.lower()
        if suffix == ".docx":
            return parse_docx(target)
        elif suffix == ".pdf":
            return parse_pdf(target)
        else:
            return target.read_text()

    # Fallback: generate resume text from profile.json
    print("⚠️  No resume file found — using profile.json as fallback.")
    return _profile_to_text(PROFILE)


def _profile_to_text(profile: dict) -> str:
    """Convert profile.json into a plain-text resume summary."""
    skills = profile.get("skills", {})
    all_skills = []
    for category, items in skills.items():
        all_skills.extend(items)

    edu = profile.get("education", [])
    edu_str = "\n".join(
        f"  - {e['degree']} from {e['institution']} ({e['year']})" for e in edu
    )

    return f"""
NAME: {profile.get('name', 'N/A')}
TITLE: {profile.get('title', 'N/A')}
LOCATION: {profile.get('location', 'N/A')}
EXPERIENCE: {profile.get('experience_years', 'N/A')} years

SUMMARY:
{profile.get('summary', '')}

SKILLS:
{', '.join(all_skills)}

EDUCATION:
{edu_str}
""".strip()
