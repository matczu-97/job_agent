"""
core/text_utils.py
Normalize LLM output to plain ASCII-friendly text for resumes and letters.
"""

import re
from typing import Any

# Common AI / Unicode punctuation → ASCII equivalents
_CHAR_REPLACEMENTS = {
    "\u2014": "-",   # em dash —
    "\u2013": "-",   # en dash –
    "\u2012": "-",   # figure dash
    "\u2010": "-",   # hyphen
    "\u2011": "-",   # non-breaking hyphen
    "\u2212": "-",   # minus sign
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201a": "'",   # single low quote
    "\u201b": "'",
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u201e": '"',
    "\u201f": '"',
    "\u00ab": '"',   # guillemets
    "\u00bb": '"',
    "\u2026": "...", # ellipsis
    "\u00a0": " ",   # non-breaking space
    "\u2009": " ",   # thin space
    "\u200a": " ",
    "\u200b": "",    # zero-width space
    "\u200c": "",
    "\u200d": "",
    "\ufeff": "",    # BOM
    "\u2192": "->",  # arrow
    "\u2190": "<-",
    "\u2022": "-",   # bullet (inline)
    "\u25cf": "-",
    "\u25aa": "-",
    "\u00b7": "-",   # middle dot
}


def sanitize_plain_text(text: str) -> str:
    """Replace typographic / AI-style Unicode with plain ASCII punctuation."""
    if not text:
        return text

    for old, new in _CHAR_REPLACEMENTS.items():
        text = text.replace(old, new)

    # Normalize dash spacing: "word - word" not "word  -  word"
    text = re.sub(r"\s*-\s*", " - ", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def sanitize_llm_object(obj: Any) -> Any:
    """Recursively sanitize all strings in an LLM JSON response."""
    if isinstance(obj, str):
        return sanitize_plain_text(obj)
    if isinstance(obj, dict):
        return {key: sanitize_llm_object(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [sanitize_llm_object(item) for item in obj]
    return obj
