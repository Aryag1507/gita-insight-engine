"""Thin CRUD helpers used by both scrapers and API."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Acharya, Commentary, Insight, Verse


# ── Verses ──────────────────────────────────────────────────────────────────

async def get_verse(session: AsyncSession, chapter: int, verse_label: str) -> Optional[Verse]:
    result = await session.execute(
        select(Verse).where(Verse.chapter == chapter, Verse.verse_label == verse_label)
    )
    return result.scalar_one_or_none()


async def upsert_verse(session: AsyncSession, **kwargs) -> Verse:
    verse = await get_verse(session, kwargs["chapter"], kwargs["verse_label"])
    if verse is None:
        verse = Verse(**kwargs)
        session.add(verse)
    else:
        for k, v in kwargs.items():
            setattr(verse, k, v)
    await session.flush()
    return verse


async def list_verses(session: AsyncSession, chapter: Optional[int] = None) -> list[Verse]:
    q = select(Verse).order_by(Verse.chapter, Verse.verse)
    if chapter is not None:
        q = q.where(Verse.chapter == chapter)
    result = await session.execute(q)
    return list(result.scalars())


# ── Commentaries ─────────────────────────────────────────────────────────────

async def upsert_commentary(
    session: AsyncSession, verse_id: int, acharya: Acharya, text: str, source_url: str = None
) -> Commentary:
    result = await session.execute(
        select(Commentary).where(
            Commentary.verse_id == verse_id, Commentary.acharya == acharya
        )
    )
    commentary = result.scalar_one_or_none()
    if commentary is None:
        commentary = Commentary(verse_id=verse_id, acharya=acharya, text=text, source_url=source_url)
        session.add(commentary)
    else:
        commentary.text = text
        commentary.source_url = source_url
    await session.flush()
    return commentary


async def get_commentaries_for_verse(session: AsyncSession, verse_id: int) -> list[Commentary]:
    result = await session.execute(
        select(Commentary).where(Commentary.verse_id == verse_id)
    )
    return list(result.scalars())


# ── Insights ─────────────────────────────────────────────────────────────────

async def get_verse_with_all(session: AsyncSession, chapter: int, verse_label: str) -> Optional[Verse]:
    result = await session.execute(
        select(Verse)
        .where(Verse.chapter == chapter, Verse.verse_label == verse_label)
        .options(
            selectinload(Verse.commentaries),
            selectinload(Verse.insights),
        )
    )
    return result.scalar_one_or_none()


async def upsert_insight(session: AsyncSession, verse_id: int, **kwargs) -> Insight:
    result = await session.execute(
        select(Insight).where(Insight.verse_id == verse_id)
    )
    insight = result.scalar_one_or_none()
    if insight is None:
        insight = Insight(verse_id=verse_id, **kwargs)
        session.add(insight)
    else:
        for k, v in kwargs.items():
            setattr(insight, k, v)
    await session.flush()
    return insight
