"""
CLI entry point for scraping and storing commentaries.

Usage:
    python ingest.py --chapters 1        # single chapter
    python ingest.py --chapters 1-3      # range
    python ingest.py --chapters 1-18     # all
"""
import asyncio
import argparse
import sys

sys.path.insert(0, ".")

from db.session import init_db, AsyncSessionLocal
from db.crud import upsert_verse, upsert_commentary
from db.models import Acharya
from scrapers.vedabase import scrape_chapters


def parse_chapters(spec: str) -> list[int]:
    if "-" in spec:
        start, end = spec.split("-")
        return list(range(int(start), int(end) + 1))
    return [int(spec)]


async def main(chapters: list[int]) -> None:
    await init_db()

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
        print(f"  ✓ BG {verse.chapter}.{verse.verse_label}")

    await scrape_chapters(chapters, on_verse=on_verse)
    print(f"\nDone. {saved} verses saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapters", default="1", help="e.g. 1 or 1-3 or 1-18")
    args = parser.parse_args()
    chapters = parse_chapters(args.chapters)
    asyncio.run(main(chapters))
