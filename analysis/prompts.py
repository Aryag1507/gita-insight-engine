"""Prompt templates for Claude-based commentary analysis."""

SYSTEM_PROMPT = """\
You are a scholar of Vaishnava philosophy specializing in Bhagavad-gita commentaries. \
You have deep knowledge of the Gaudiya Vaishnava tradition and the distinct philosophical \
emphases of each acharya. Your analysis is precise, grounded in the text, and avoids \
speculation beyond what the commentaries actually say.\
"""

ANALYSIS_PROMPT_TEMPLATE = """\
You are analyzing commentaries on Bhagavad-gita {chapter}.{verse_label}.

VERSE:
{sanskrit}

Translation: {translation}

COMMENTARIES:
{commentary_sections}

---

Analyze these commentaries and respond with ONLY valid JSON in exactly this structure:

{{
  "themes": [
    {{
      "theme": "short theme name",
      "description": "1-2 sentence explanation of this theme",
      "acharyas": ["list of acharyas who address this theme"]
    }}
  ],
  "agreements": [
    {{
      "point": "a philosophical point all listed acharyas agree on",
      "acharyas": ["acharyas who share this view"]
    }}
  ],
  "divergences": [
    {{
      "point": "the topic where they diverge",
      "positions": {{
        "acharya_name": "their specific stance or emphasis on this point"
      }}
    }}
  ],
  "synthesis": "A single flowing paragraph (4-6 sentences) that unifies the key philosophical insight of this verse as understood across the commentaries. Highlight what is universally agreed upon and note the most significant divergence."
}}

Rules:
- Use only acharya names that appear in the commentaries provided: {acharya_names}
- themes: 2-4 themes maximum
- agreements: only include points explicitly stated by 2+ acharyas
- divergences: only include real differences in emphasis or interpretation, not minor wording
- synthesis: written for an intelligent reader, not an academic — clear and illuminating
- Return ONLY the JSON object, no markdown fences, no explanation
"""


def build_commentary_sections(commentaries: list[dict]) -> str:
    """Format list of {acharya, text} dicts into prompt section."""
    sections = []
    for c in commentaries:
        acharya = c["acharya"].replace("_", " ").title()
        sections.append(f"[{acharya}]\n{c['text']}")
    return "\n\n".join(sections)


def build_analysis_prompt(
    chapter: int,
    verse_label: str,
    sanskrit: str,
    translation: str,
    commentaries: list[dict],
) -> str:
    acharya_names = [c["acharya"].replace("_", " ").title() for c in commentaries]
    return ANALYSIS_PROMPT_TEMPLATE.format(
        chapter=chapter,
        verse_label=verse_label,
        sanskrit=sanskrit or "(Sanskrit not available)",
        translation=translation or "(Translation not available)",
        commentary_sections=build_commentary_sections(commentaries),
        acharya_names=", ".join(acharya_names),
    )
