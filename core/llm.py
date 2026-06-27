"""
core/llm.py
Thin wrapper around the Anthropic SDK.
All agents use this — swap the model in one place.
"""

import json
import anthropic
from core.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def ask(
    prompt: str,
    system: str = "",
    max_tokens: int = 2000,
    json_mode: bool = False,
) -> str:
    """
    Send a prompt to Claude and return the text response.

    Args:
        prompt:     The user message.
        system:     Optional system prompt.
        max_tokens: Max tokens in response.
        json_mode:  If True, appends a JSON instruction and parses the result.

    Returns:
        str (or dict if json_mode=True)
    """
    messages = [{"role": "user", "content": prompt}]

    if json_mode:
        system = (system + "\n\nYou must respond with valid JSON only. "
                  "No explanation, no markdown, no code fences. Raw JSON only.").strip()

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system if system else anthropic.NOT_GIVEN,
        messages=messages,
    )

    text = response.content[0].text.strip()

    if json_mode:
        # Strip accidental markdown fences
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)

    return text


def ask_with_history(messages: list[dict], system: str = "", max_tokens: int = 2000) -> str:
    """Multi-turn conversation. messages = [{"role": "user"/"assistant", "content": "..."}]"""
    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system if system else anthropic.NOT_GIVEN,
        messages=messages,
    )
    return response.content[0].text.strip()
