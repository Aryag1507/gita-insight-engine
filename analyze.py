"""
CLI entry point for running AI analysis on stored commentaries.

Usage:
    python analyze.py --chapters 1        # analyze all verses in chapter 1
    python analyze.py --chapters 1-3      # range
    python analyze.py --chapters 1-18     # all
    python analyze.py --verse 2.47        # single verse
    python analyze.py --chapters 1 --min-acharyas 3   # only verses with all 3
"""
import asyncio
import argparse
import json
import sys

sys.path.insert(0, ".")

from db.session import init_db, AsyncSessionLocal
from db.crud import list_verses, get_commentaries_for_verse, upsert_insight
from analysis.engine import analyze_verse


def parse_chapters(spec: str) -> list[int]:
    if "-" in spec:
        start, end = spec.split("-")
        return list(range(int(start), int(end) + 1))
    return [int(spec)]


async def run_analysis(
    chapters: list[int],
    min_acharyas: int = 2,
    single_verse: str = None,
) -> None:
    await init_db()

    total_analyzed = 0
    total_skipped = 0
    total_tokens = 0

    async with AsyncSessionLocal() as session:
        verses = await list_verses(session, chapter=chapters[0] if len(chapters) == 1 else None)

        # Filter by chapters and optionally a single verse
        if single_verse:
            ch_str, v_str = single_verse.split(".")
            verses = [v for v in verses if v.chapter == int(ch_str) and v.verse_label == v_str]
        else:
            verses = [v for v in verses if v.chapter in chapters]

    for verse in verses:
        async with AsyncSessionLocal() as session:
            commentaries = await get_commentaries_for_verse(session, verse.id)

        if len(commentaries) < min_acharyas:
            print(f"  — BG {verse.chapter}.{verse.verse_label}: only {len(commentaries)} commentary/ies, skipping")
            total_skipped += 1
            continue

        commentary_dicts = [
            {"acharya": c.acharya.value, "text": c.text}
            for c in commentaries
        ]
        acharya_names = [c.acharya.value for c in commentaries]

        print(f"  Analyzing BG {verse.chapter}.{verse.verse_label} "
              f"[{', '.join(acharya_names)}]...", end=" ", flush=True)

        try:
            result = analyze_verse(
                chapter=verse.chapter,
                verse_label=verse.verse_label,
                sanskrit=verse.sanskrit or "",
                translation=verse.translation or "",
                commentaries=commentary_dicts,
            )
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        if not result:
            print("skipped (insufficient data)")
            total_skipped += 1
            continue

        tokens_used = result.get("_input_tokens", 0) + result.get("_output_tokens", 0)
        total_tokens += tokens_used
        print(f"✓ ({tokens_used} tokens, {len(result.get('themes', []))} themes, "
              f"{len(result.get('agreements', []))} agreements, "
              f"{len(result.get('divergences', []))} divergences)")

        # Save to DB
        async with AsyncSessionLocal() as session:
            await upsert_insight(
                session,
                verse_id=verse.id,
                acharyas_included=",".join(acharya_names),
                themes_json=json.dumps(result.get("themes", [])),
                agreements_json=json.dumps(result.get("agreements", [])),
                divergences_json=json.dumps(result.get("divergences", [])),
                synthesis=result.get("synthesis", ""),
                model_used=result.get("_model", ""),
            )
            await session.commit()

        total_analyzed += 1

    print(f"\nDone. {total_analyzed} verses analyzed, {total_skipped} skipped.")
    print(f"Total tokens used: {total_tokens:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapters", default="1")
    parser.add_argument("--verse", help="Single verse e.g. 2.47")
    parser.add_argument("--min-acharyas", type=int, default=2,
                        help="Minimum number of commentaries required (default 2)")
    args = parser.parse_args()

    chapters = parse_chapters(args.chapters)
    asyncio.run(run_analysis(
        chapters=chapters,
        min_acharyas=args.min_acharyas,
        single_verse=args.verse,
    ))
