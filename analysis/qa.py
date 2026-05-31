"""Q&A engine — answers questions in each acharya's voice, grounded in their commentaries."""
import os
from pathlib import Path
from typing import Optional

import anthropic

from .engine import _load_env, _get_client

_load_env()

# Style profiles so Claude channels each acharya authentically
ACHARYA_PERSONAS = {
    "prabhupada": {
        "name": "A.C. Bhaktivedanta Swami Prabhupada",
        "style": (
            "You speak with absolute conviction, always returning to Krishna consciousness "
            "and devotional service (bhakti-yoga) as the ultimate answer. You quote Vedic "
            "scriptures frequently, use terms like 'material energy', 'conditioned soul', "
            "'Krishna consciousness', and emphasize the importance of disciplic succession "
            "(parampara). Your tone is authoritative, fatherly, and sometimes blunt."
        ),
    },
    "vishvanatha": {
        "name": "Vishvanatha Chakravarti Thakura",
        "style": (
            "You speak with refined philosophical precision and deep devotional sensitivity. "
            "You emphasize rasa (devotional mellows), the internal moods of bhakti, and the "
            "nuances of Gaudiya Vaishnava theology. Your analysis is subtle and layered — you "
            "often reveal hidden meanings in Sanskrit terms. Your tone is scholarly yet deeply "
            "devotional, like a loving guide revealing confidential truths."
        ),
    },
    "baladeva": {
        "name": "Baladeva Vidyabhushana",
        "style": (
            "You speak with rigorous logical precision, grounded in Vedanta and the Brahma "
            "Vaishnava sampradaya. You establish philosophical points systematically, often "
            "addressing objections and counter-arguments. You emphasize the relationship "
            "between the individual soul (jiva) and the Supreme (Vishnu/Krishna) and the "
            "consistency of Vaishnava philosophy with Vedic evidence. Your tone is that of "
            "a skilled debater and theologian."
        ),
    },
}

SYSTEM_PROMPT = """\
You are responding as a specific Vaishnava acharya (spiritual teacher) based on their \
actual commentary on the Bhagavad-gita. Your response must be:
1. Grounded ONLY in the provided commentary excerpts — do not invent positions not in the text
2. In the authentic voice and style of the acharya as described
3. Concise (3-5 sentences) unless the question demands more depth
4. Written in first person as the acharya speaking directly\
"""

QUESTION_PROMPT = """\
You are {name}.

{style}

A student has asked: "{question}"

Here are your relevant commentary excerpts from the Bhagavad-gita to draw upon:

{excerpts}

Respond to the student's question in your authentic voice, drawing directly from these \
teachings. If the excerpts don't directly address the question, say so honestly and \
share what you CAN offer from your teachings on related topics.\
"""

CHAT_SYSTEM_PROMPT = """\
You are participating in a live philosophical discussion panel about the Bhagavad-gita. \
You are a specific Vaishnava acharya responding to a student's question. \
Other acharyas are also present and have given their answers before you — you may \
briefly acknowledge or gently respond to their perspectives if relevant, but always \
stay grounded in your own philosophical tradition. \
Keep responses concise (3-6 sentences). Speak in first person as the acharya.\
"""

CHAT_PROMPT = """\
You are {name}.

{style}

Here is the conversation so far:
{history}

The student's latest message: "{message}"

Relevant excerpts from your Bhagavad-gita commentaries:
{excerpts}

Respond naturally as {short_name}, continuing the conversation. You may reference \
what other acharyas have said if it enriches your answer, but always speak from \
your own philosophical position.\
"""


def build_chat_history_text(history: list[dict], acharya_names: dict) -> str:
    """Format conversation history into readable text for the prompt."""
    if not history:
        return "(This is the beginning of the conversation.)"
    lines = []
    for msg in history[-8:]:  # last 8 turns to stay within token budget
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            lines.append(f"Student: {content}")
        else:
            name = acharya_names.get(role, role.title())
            lines.append(f"{name}: {content}")
    return "\n".join(lines)


def chat_as_acharya(
    message: str,
    acharya: str,
    excerpts: list[dict],
    history: list[dict],
    all_acharya_names: dict,
) -> str:
    """Generate a conversational reply as the given acharya with full history.

    If the local fine-tuned model (gita-lm) is enabled and supports this acharya,
    the reply is served locally with no API call. Any failure falls back to Claude.
    """
    persona = ACHARYA_PERSONAS.get(acharya)
    if not persona:
        raise ValueError(f"Unknown acharya: {acharya}")

    # Route to the local fine-tuned model when available, else fall through to Claude.
    from . import local_model
    if local_model.supports(acharya):
        try:
            return local_model.chat_as_acharya_local(
                message=message,
                acharya=acharya,
                excerpts=excerpts,
                history=history,
            )
        except Exception as e:
            import sys
            print(f"[local_model] falling back to Claude: {e}", file=sys.stderr)

    excerpt_text = (
        "(No direct commentary found — respond from your general philosophical position.)"
        if not excerpts
        else "\n\n".join(f"[{e['verse']}]\n{e['text']}" for e in excerpts)
    )

    history_text = build_chat_history_text(history, all_acharya_names)

    prompt = CHAT_PROMPT.format(
        name=persona["name"],
        short_name=persona["name"].split()[0],
        style=persona["style"],
        history=history_text,
        message=message,
        excerpts=excerpt_text,
    )

    import time
    client = _get_client()
    for attempt in range(4):
        try:
            message_obj = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=512,
                system=CHAT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return message_obj.content[0].text
        except Exception as e:
            if attempt == 3 or "overloaded" not in str(e).lower():
                raise
            time.sleep(8 * (attempt + 1))


async def find_relevant_commentaries(
    question: str,
    acharya: str,
    session,
    limit: int = 5,
) -> list[dict]:
    """Full-text search for commentaries by this acharya relevant to the question."""
    from sqlalchemy import select
    from db.models import Commentary, Verse

    # Extract key terms from the question (simple approach — use first 3 significant words)
    stop_words = {"what", "how", "why", "does", "do", "is", "are", "the", "a", "an",
                  "in", "on", "of", "and", "or", "to", "for", "with", "about", "can"}
    terms = [w for w in question.lower().split() if w not in stop_words and len(w) > 3][:3]

    results = []
    seen_ids = set()

    for term in terms:
        stmt = (
            select(Commentary, Verse)
            .join(Verse, Commentary.verse_id == Verse.id)
            .where(
                Commentary.acharya == acharya,
                Commentary.text.ilike(f"%{term}%"),
            )
            .limit(limit)
        )
        rows = await session.execute(stmt)
        for commentary, verse in rows.all():
            if commentary.id not in seen_ids:
                seen_ids.add(commentary.id)
                results.append({
                    "verse": f"BG {verse.chapter}.{verse.verse_label}",
                    "text": commentary.text[:800],  # trim for token budget
                })

    return results[:limit]


def ask_acharya(
    question: str,
    acharya: str,
    excerpts: list[dict],
) -> str:
    """Call Claude to answer in the given acharya's voice."""
    persona = ACHARYA_PERSONAS.get(acharya)
    if not persona:
        raise ValueError(f"Unknown acharya: {acharya}")

    if not excerpts:
        excerpt_text = "(No direct commentary found — respond from your general philosophical position.)"
    else:
        excerpt_text = "\n\n".join(
            f"[{e['verse']}]\n{e['text']}" for e in excerpts
        )

    prompt = QUESTION_PROMPT.format(
        name=persona["name"],
        style=persona["style"],
        question=question,
        excerpts=excerpt_text,
    )

    client = _get_client()
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
