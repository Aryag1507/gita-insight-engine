"""AI analysis engine — calls Claude to analyze cross-acharya commentaries."""
import json
import os
import re
from pathlib import Path
from typing import Optional

import anthropic

from .prompts import SYSTEM_PROMPT, build_analysis_prompt

# Haiku is ~4x cheaper than Sonnet and plenty capable for structured extraction.
# Cost estimate: ~$0.08 per chapter vs ~$0.45 with Sonnet.
MODEL = "claude-haiku-4-5"
MAX_TOKENS = 1024

# Max characters per commentary sent to Claude.
# Prabhupada purports average 3k chars — most insight is in the first ~1500.
COMMENTARY_MAX_CHARS = 1500

# Load .env manually (no extra dep needed)
def _load_env() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                key = k.strip()
                val = v.strip().strip('"').strip("'")
                if val:  # only set if non-empty, always override
                    os.environ[key] = val

_load_env()


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Create a .env file or export the variable."
        )
    return anthropic.Anthropic(api_key=api_key)


def _extract_json(text: str) -> dict:
    """Extract JSON from Claude's response, handling any stray whitespace."""
    text = text.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def analyze_verse(
    chapter: int,
    verse_label: str,
    sanskrit: str,
    translation: str,
    commentaries: list[dict],  # [{acharya, text}, ...]
) -> Optional[dict]:
    """
    Call Claude to analyze commentaries for one verse.
    Returns structured dict with themes, agreements, divergences, synthesis.
    Returns None if fewer than 2 commentaries are available.
    """
    if len(commentaries) < 2:
        return None

    # Truncate long commentaries to reduce token cost
    trimmed = [
        {**c, "text": c["text"][:COMMENTARY_MAX_CHARS] + ("…" if len(c["text"]) > COMMENTARY_MAX_CHARS else "")}
        for c in commentaries
    ]

    client = _get_client()
    prompt = build_analysis_prompt(
        chapter, verse_label, sanskrit, translation, trimmed
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    result = _extract_json(raw)

    # Attach metadata
    result["_model"] = message.model
    result["_input_tokens"] = message.usage.input_tokens
    result["_output_tokens"] = message.usage.output_tokens

    return result
