"""Debate engine — acharyas converse with each other, not just the user."""
import asyncio
from analysis.engine import _load_env, _get_client
from analysis.qa import ACHARYA_PERSONAS, find_relevant_commentaries

_load_env()

# Fixed rotation order
DEBATE_ORDER = ["prabhupada", "vishvanatha", "baladeva"]

# Each acharya has a standing philosophical tension they press
DEBATE_ROLES = {
    "prabhupada": (
        "You are the authoritative anchor of this debate. You speak with conviction and "
        "always ground the discussion in Krishna consciousness and devotional service. "
        "When others drift toward impersonalism, dry knowledge, or abstract philosophy, "
        "you firmly but respectfully bring them back to the personal God and bhakti. "
        "You are not rude, but you do not compromise on siddhanta (philosophical conclusions). "
        "Press Vishvanatha when he is too esoteric; press Baladeva when he is too academic."
    ),
    "vishvanatha": (
        "You are the devotional refiner of this debate. You find the deeper rasa — the "
        "emotional and relational dimension — in every philosophical point. When Prabhupada "
        "is too direct or institutional, you reveal the inner sweetness. When Baladeva is "
        "too logical, you show what logic alone cannot reach. You are gentle but persistent "
        "in pointing toward the confidential bhakti teachings that transcend both karma and jnana. "
        "Find the nuance others miss."
    ),
    "baladeva": (
        "You are the logical challenger of this debate. You demand philosophical precision. "
        "When claims are made without Vedic evidence or logical grounding, you press for "
        "justification. You respect both Prabhupada and Vishvanatha deeply, but you will "
        "point out when an argument is incomplete, when a term is being used loosely, or "
        "when a conclusion doesn't follow from its premises. You are rigorous, not combative. "
        "You build on what others say and refine it systematically."
    ),
}

SYSTEM_PROMPT = """\
You are one of three Vaishnava acharyas engaged in a live philosophical debate about the \
Bhagavad-gita. You are speaking TO the other acharyas, not to the student. \
The student may occasionally interject with a question or direction — acknowledge it briefly \
then engage with your fellow acharyas. \
Keep your response to 4-6 sentences. Be direct. Philosophical debates require clarity, not \
lengthy monologues. Do not just agree — find the point of genuine tension or refinement and \
press it. Speak in first person.\
"""

DEBATE_PROMPT = """\
You are {name}.

Your philosophical role in this debate:
{role}

The debate topic: "{topic}"

Debate so far:
{history}

{injected_note}

Relevant excerpts from your Bhagavad-gita commentaries to draw upon:
{excerpts}

Now speak. Address your fellow acharyas directly. Find the point of genuine \
philosophical tension or refinement and press it. Be concise and sharp.\
"""


def next_speaker(current: str) -> str:
    idx = DEBATE_ORDER.index(current)
    return DEBATE_ORDER[(idx + 1) % len(DEBATE_ORDER)]


def build_debate_history(history: list[dict], acharya_names: dict) -> str:
    if not history:
        return "(The debate has not yet begun.)"
    lines = []
    for msg in history[-10:]:  # last 10 turns
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            lines.append(f"[Student interjects]: {content}")
        elif role == "topic":
            lines.append(f"[Debate topic set]: {content}")
        else:
            name = acharya_names.get(role, role.title())
            lines.append(f"{name}: {content}")
    return "\n\n".join(lines)


def generate_debate_turn(
    speaker: str,
    topic: str,
    history: list[dict],
    excerpts: list[dict],
    user_interjection: str = None,
) -> str:
    persona = ACHARYA_PERSONAS[speaker]
    all_names = {k: v["name"] for k, v in ACHARYA_PERSONAS.items()}

    excerpt_text = (
        "(No direct commentary found — draw from your general philosophical position.)"
        if not excerpts
        else "\n\n".join(f"[{e['verse']}]\n{e['text']}" for e in excerpts)
    )

    history_text = build_debate_history(history, all_names)

    injected = ""
    if user_interjection:
        injected = f'The student has just interjected: "{user_interjection}"\nAcknowledge this briefly, then continue engaging with your fellow acharyas.'

    prompt = DEBATE_PROMPT.format(
        name=persona["name"],
        role=DEBATE_ROLES[speaker],
        topic=topic,
        history=history_text,
        excerpts=excerpt_text,
        injected_note=injected,
    )

    client = _get_client()
    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text
