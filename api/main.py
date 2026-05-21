"""FastAPI application — Commentary Aggregator & Insight Engine."""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Commentary, Insight, Verse
from db.session import get_session, init_db
from db.crud import get_verse_with_all, list_verses
from api.schemas import (
    CommentaryOut, InsightOut, SearchResult, VerseDetailOut, VerseOut
)
from analysis.qa import find_relevant_commentaries, ask_acharya, chat_as_acharya, ACHARYA_PERSONAS


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Gita Insight Engine",
    description="Multi-acharya Bhagavad-gita commentary aggregator with AI synthesis",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)


# ── Verses ────────────────────────────────────────────────────────────────────

@app.get("/verses", response_model=list[VerseOut], tags=["Verses"])
async def list_all_verses(
    chapter: Optional[int] = Query(None, description="Filter by chapter number"),
    session: AsyncSession = Depends(get_session),
):
    """List all verses, optionally filtered by chapter."""
    verses = await list_verses(session, chapter=chapter)
    return verses


@app.get("/verses/{chapter}/{verse_label}", response_model=VerseDetailOut, tags=["Verses"])
async def get_verse(
    chapter: int,
    verse_label: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get a single verse with all commentaries and AI insight.
    verse_label can be a number (e.g. 47) or a range (e.g. 4-6).
    """
    verse = await get_verse_with_all(session, chapter, verse_label)
    if not verse:
        raise HTTPException(status_code=404, detail=f"BG {chapter}.{verse_label} not found")

    insight_out = None
    if verse.insights:
        insight_out = InsightOut.model_validate(verse.insights[-1])

    return VerseDetailOut(
        chapter=verse.chapter,
        verse_label=verse.verse_label,
        sanskrit=verse.sanskrit,
        transliteration=verse.transliteration,
        word_for_word=verse.word_for_word,
        translation=verse.translation,
        commentaries=[
            CommentaryOut(
                acharya=c.acharya.value,
                text=c.text,
                source_url=c.source_url,
            )
            for c in verse.commentaries
        ],
        insight=insight_out,
    )


# ── Commentaries ──────────────────────────────────────────────────────────────

@app.get("/verses/{chapter}/{verse_label}/commentaries",
         response_model=list[CommentaryOut], tags=["Commentaries"])
async def get_commentaries(
    chapter: int,
    verse_label: str,
    acharya: Optional[str] = Query(None, description="Filter by acharya name"),
    session: AsyncSession = Depends(get_session),
):
    """Get all commentaries for a verse, optionally filtered by acharya."""
    verse = await get_verse_with_all(session, chapter, verse_label)
    if not verse:
        raise HTTPException(status_code=404, detail=f"BG {chapter}.{verse_label} not found")

    commentaries = verse.commentaries
    if acharya:
        commentaries = [c for c in commentaries if c.acharya.value == acharya.lower()]

    return [
        CommentaryOut(acharya=c.acharya.value, text=c.text, source_url=c.source_url)
        for c in commentaries
    ]


# ── Insights ──────────────────────────────────────────────────────────────────

@app.get("/verses/{chapter}/{verse_label}/insight",
         response_model=InsightOut, tags=["Insights"])
async def get_insight(
    chapter: int,
    verse_label: str,
    session: AsyncSession = Depends(get_session),
):
    """Get the AI-generated insight for a verse."""
    verse = await get_verse_with_all(session, chapter, verse_label)
    if not verse:
        raise HTTPException(status_code=404, detail=f"BG {chapter}.{verse_label} not found")
    if not verse.insights:
        raise HTTPException(
            status_code=404,
            detail=f"No insight generated yet for BG {chapter}.{verse_label}. "
                   "Run: python analyze.py --verse {chapter}.{verse_label}"
        )
    return InsightOut.model_validate(verse.insights[-1])


# ── Search ────────────────────────────────────────────────────────────────────

@app.get("/search", response_model=list[SearchResult], tags=["Search"])
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    acharya: Optional[str] = Query(None, description="Limit to one acharya"),
    chapter: Optional[int] = Query(None, description="Limit to one chapter"),
    limit: int = Query(20, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Full-text search across all commentary texts."""
    stmt = (
        select(Commentary, Verse)
        .join(Verse, Commentary.verse_id == Verse.id)
        .where(Commentary.text.ilike(f"%{q}%"))
    )
    if acharya:
        stmt = stmt.where(Commentary.acharya == acharya.lower())
    if chapter:
        stmt = stmt.where(Verse.chapter == chapter)
    stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    rows = result.all()

    results = []
    for commentary, verse in rows:
        # Find snippet around the match
        text_lower = commentary.text.lower()
        idx = text_lower.find(q.lower())
        start = max(0, idx - 80)
        end = min(len(commentary.text), idx + 80 + len(q))
        snippet = ("..." if start > 0 else "") + commentary.text[start:end] + ("..." if end < len(commentary.text) else "")

        results.append(SearchResult(
            chapter=verse.chapter,
            verse_label=verse.verse_label,
            translation=verse.translation,
            matched_acharya=commentary.acharya.value,
            snippet=snippet,
        ))

    return results


# ── Q&A ───────────────────────────────────────────────────────────────────────

from pydantic import BaseModel

class QuestionRequest(BaseModel):
    question: str

class AcharyaAnswer(BaseModel):
    acharya: str
    name: str
    answer: str
    source_verses: list[str]

class QAResponse(BaseModel):
    question: str
    answers: list[AcharyaAnswer]

# ── Chat models ───────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str          # "user" | "prabhupada" | "vishvanatha" | "baladeva"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    acharyas: list[str] = []   # if non-empty, only these acharyas respond

class ChatTurn(BaseModel):
    acharya: str
    name: str
    reply: str
    source_verses: list[str]

class ChatResponse(BaseModel):
    message: str
    replies: list[ChatTurn]


# ── Debate models ─────────────────────────────────────────────────────────────

class DebateMessage(BaseModel):
    role: str      # "prabhupada" | "vishvanatha" | "baladeva" | "user" | "topic"
    content: str

class DebateRequest(BaseModel):
    topic: str
    history: list[DebateMessage] = []
    turns: int = 3                      # how many new turns to generate
    user_interjection: str = ""         # optional student question mid-debate

class DebateTurn(BaseModel):
    speaker: str
    name: str
    content: str
    source_verses: list[str]

class DebateResponse(BaseModel):
    topic: str
    turns: list[DebateTurn]


@app.post("/debate", response_model=DebateResponse, tags=["Q&A"])
async def debate(req: DebateRequest):
    """
    Run one or more turns of an inter-acharya philosophical debate.
    Pass the full history on each request; the API returns the next N turns.
    Optionally inject a student question via user_interjection.
    """
    from analysis.debate import generate_debate_turn, next_speaker, DEBATE_ORDER
    from db.session import AsyncSessionLocal
    import asyncio

    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Debate topic cannot be empty.")

    history = [m.model_dump() for m in req.history]

    # Determine the first speaker: whoever follows the last acharya in history
    last_speaker = next(
        (m["role"] for m in reversed(history) if m["role"] in DEBATE_ORDER),
        DEBATE_ORDER[-1],   # if no acharya has spoken yet, start with first
    )

    new_turns: list[DebateTurn] = []
    interjection = req.user_interjection.strip() or None

    for i in range(req.turns):
        speaker = next_speaker(last_speaker)

        # Fetch relevant excerpts for this speaker
        async with AsyncSessionLocal() as s:
            excerpts = await find_relevant_commentaries(topic, speaker, s)

        # Pass interjection only on the first new turn
        reply_text = await asyncio.get_event_loop().run_in_executor(
            None,
            generate_debate_turn,
            speaker,
            topic,
            history,
            excerpts,
            interjection if i == 0 else None,
        )

        turn = DebateTurn(
            speaker=speaker,
            name=ACHARYA_PERSONAS[speaker]["name"],
            content=reply_text,
            source_verses=[e["verse"] for e in excerpts],
        )
        new_turns.append(turn)

        # Append to history so each subsequent speaker can "hear" the previous one
        history.append({"role": speaker, "content": reply_text})
        last_speaker = speaker

    return DebateResponse(topic=topic, turns=new_turns)


@app.post("/ask", response_model=QAResponse, tags=["Q&A"])
async def ask(
    req: QuestionRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Ask a question and receive answers in the voice of each acharya,
    grounded in their actual Bhagavad-gita commentaries.
    """
    from analysis.qa import ACHARYA_PERSONAS
    import asyncio

    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    ACHARYAS = ["prabhupada", "vishvanatha", "baladeva"]

    # Fetch relevant excerpts — each acharya gets its own session to avoid concurrency conflict
    from db.session import AsyncSessionLocal
    async def fetch(acharya):
        async with AsyncSessionLocal() as s:
            return await find_relevant_commentaries(question, acharya, s)

    excerpt_lists = await asyncio.gather(*[fetch(a) for a in ACHARYAS])

    # Call Claude for each acharya (run in thread pool to avoid blocking)
    answers = []
    for acharya, excerpts in zip(ACHARYAS, excerpt_lists):
        try:
            answer_text = await asyncio.get_event_loop().run_in_executor(
                None, ask_acharya, question, acharya, excerpts
            )
        except Exception as e:
            answer_text = f"(Could not generate response: {e})"

        answers.append(AcharyaAnswer(
            acharya=acharya,
            name=ACHARYA_PERSONAS[acharya]["name"],
            answer=answer_text,
            source_verses=[e["verse"] for e in excerpts],
        ))

    return QAResponse(question=question, answers=answers)


@app.post("/chat", response_model=ChatResponse, tags=["Q&A"])
async def chat(
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Multi-turn panel conversation with all three acharyas.
    Pass the full history of the conversation on each request.
    """
    import asyncio

    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    ALL_ACHARYAS = ["prabhupada", "vishvanatha", "baladeva"]
    ACHARYAS = [a for a in ALL_ACHARYAS if a in req.acharyas] if req.acharyas else ALL_ACHARYAS
    all_acharya_names = {k: v["name"] for k, v in ACHARYA_PERSONAS.items()}
    history = [m.model_dump() for m in req.history]

    # Fetch relevant excerpts concurrently (each gets its own session)
    from db.session import AsyncSessionLocal
    async def fetch(acharya):
        async with AsyncSessionLocal() as s:
            return await find_relevant_commentaries(message, acharya, s)

    excerpt_lists = await asyncio.gather(*[fetch(a) for a in ACHARYAS])

    # Call Claude for each acharya with conversation history
    replies = []
    # Run sequentially so each acharya can "hear" the previous replies in follow-up turns
    for acharya, excerpts in zip(ACHARYAS, excerpt_lists):
        try:
            reply_text = await asyncio.get_event_loop().run_in_executor(
                None, chat_as_acharya, message, acharya, excerpts, history, all_acharya_names
            )
        except Exception as e:
            reply_text = f"(Could not generate response: {e})"

        replies.append(ChatTurn(
            acharya=acharya,
            name=ACHARYA_PERSONAS[acharya]["name"],
            reply=reply_text,
            source_verses=[e["verse"] for e in excerpts],
        ))

    return ChatResponse(message=message, replies=replies)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "version": "0.1.0"}
