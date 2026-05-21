"""
CLI entry point for scraping and storing commentaries from all three sources.

Usage:
    python ingest.py --chapters 1        # single chapter
    python ingest.py --chapters 1-3      # range
    python ingest.py --chapters 1-18     # all
    python ingest.py --chapters 1 --source vedabase     # one source only
    python ingest.py --chapters 1 --source wisdomlib
    python ingest.py --chapters 1 --source bgorg
"""
import asyncio
import argparse
import sys

sys.path.insert(0, ".")

from db.session import init_db, AsyncSessionLocal
from db.crud import upsert_verse, upsert_commentary, get_verse
from db.models import Acharya
from scrapers.vedabase import scrape_chapters as scrape_vedabase
from scrapers.wisdomlib import scrape_chapters as scrape_wisdomlib
from scrapers.bgorg import scrape_chapters as scrape_bgorg


def parse_chapters(spec: str) -> list[int]:
    if "-" in spec:
        start, end = spec.split("-")
        return list(range(int(start), int(end) + 1))
    return [int(spec)]


async def run_vedabase(chapters: list[int]) -> int:
    saved = 0

    async def on_verse(verse):
        nonlocal saved
        async with AsyncSessionLocal() as session:
            db_verse = await upsert_verse(
                session,
                chapter=verse.chapter,
                verse=verse.verse_number,
                verse_label=verse.verse_label,
                sanskrit=verse.sanskrit,
                transliteration=verse.transliteration,
                word_for_word=verse.word_for_word,
                translation=verse.translation,
            )
            if verse.purport:
                await upsert_commentary(
                    session,
                    verse_id=db_verse.id,
                    acharya=Acharya.PRABHUPADA,
                    text=verse.purport,
                    source_url=verse.source_url,
                )
            await session.commit()
        saved += 1
        print(f"  ✓ [Prabhupada] BG {verse.chapter}.{verse.verse_label}")

    await scrape_vedabase(chapters, on_verse=on_verse)
    return saved


async def run_wisdomlib(chapters: list[int]) -> int:
    saved = 0

    async def on_verse(verse):
        nonlocal saved
        async with AsyncSessionLocal() as session:
            # Verse row must already exist (run vedabase first)
            db_verse = await get_verse(session, verse.chapter, verse.verse_label)
            if db_verse is None:
                # Create minimal verse record if vedabase hasn't run yet
                db_verse = await upsert_verse(
                    session,
                    chapter=verse.chapter,
                    verse=int(verse.verse_label.split("-")[0]),
                    verse_label=verse.verse_label,
                )
            await upsert_commentary(
                session,
                verse_id=db_verse.id,
                acharya=Acharya.VISHVANATHA,
                text=verse.vishvanatha,
                source_url=verse.source_url,
            )
            await session.commit()
        saved += 1
        print(f"  ✓ [Vishvanatha] BG {verse.chapter}.{verse.verse_label}")

    await scrape_wisdomlib(chapters, on_verse=on_verse)
    return saved


async def run_bgorg(chapters: list[int]) -> int:
    saved = 0

    async def on_verse(verse):
        nonlocal saved
        if not verse.baladeva:
            return
        async with AsyncSessionLocal() as session:
            db_verse = await get_verse(session, verse.chapter, verse.verse_label)
            if db_verse is None:
                db_verse = await upsert_verse(
                    session,
                    chapter=verse.chapter,
                    verse=verse.verse_number,
                    verse_label=verse.verse_label,
                )
            await upsert_commentary(
                session,
                verse_id=db_verse.id,
                acharya=Acharya.BALADEVA,
                text=verse.baladeva,
                source_url=verse.source_url,
            )
            await session.commit()
        saved += 1
        print(f"  ✓ [Baladeva] BG {verse.chapter}.{verse.verse_label}")

    await scrape_bgorg(chapters, on_verse=on_verse)
    return saved


async def main(chapters: list[int], source: str) -> None:
    await init_db()
    total = 0

    if source in ("all", "vedabase"):
        n = await run_vedabase(chapters)
        total += n
        print(f"\n  Prabhupada: {n} verses saved.")

    if source in ("all", "wisdomlib"):
        n = await run_wisdomlib(chapters)
        total += n
        print(f"\n  Vishvanatha: {n} verses saved.")

    if source in ("all", "bgorg"):
        n = await run_bgorg(chapters)
        total += n
        print(f"\n  Baladeva: {n} verses saved.")

    print(f"\nDone. {total} total records saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapters", default="1", help="e.g. 1 or 1-3 or 1-18")
    parser.add_argument("--source", default="all",
                        choices=["all", "vedabase", "wisdomlib", "bgorg"],
                        help="Which source to scrape")
    args = parser.parse_args()
    asyncio.run(main(parse_chapters(args.chapters), args.source))
