"""Scraper for Baladeva Vidyabhushana's commentary from bhagavad-gita.org.

The site uses a 2×2 table layout for four Vaishnava sampradaya commentaries.
Baladeva's is presented under the Brahma Vaishnava Sampradaya cell.
"""
import re
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .base import fetch, make_client

BASE_URL = "https://www.bhagavad-gita.org/Gita"

# Chapter → verse count
CHAPTER_VERSE_COUNTS = {
    1: 46, 2: 72, 3: 43, 4: 42, 5: 29, 6: 47,
    7: 30, 8: 28, 9: 34, 10: 42, 11: 55, 12: 20,
    13: 35, 14: 27, 15: 20, 16: 24, 17: 28, 18: 78,
}

BRAHMA_LABEL = "Brahma Vaisnava Sampradaya"


@dataclass
class BgOrgVerse:
    chapter: int
    verse_number: int
    verse_label: str
    source_url: str
    baladeva: Optional[str]


def _verse_url(chapter: int, verse: int) -> str:
    return f"{BASE_URL}/verse-{chapter:02d}-{verse:02d}.html"


def _extract_baladeva(soup: BeautifulSoup) -> Optional[str]:
    """Find the Brahma Vaishnava Sampradaya table cell and return its commentary text."""
    tables = soup.find_all("table")
    # Commentary table has bgcolor="#404080" cells
    for table in tables:
        for td in table.find_all("td", recursive=True):
            u_tag = td.find("u")
            if u_tag and BRAHMA_LABEL in u_tag.get_text():
                # Remove image tags and attribution headers before extracting text
                for img in td.find_all("img"):
                    img.decompose()
                for center in td.find_all("center"):
                    center.decompose()
                text = td.get_text(separator="\n", strip=True)
                # Strip header lines up to and including the acharya attribution
                lines = text.split("\n")
                start = 0
                for i, line in enumerate(lines):
                    if any(x in line for x in ["Commentary", "Vidyabhusana", "Madhvacarya"]):
                        start = i + 1
                # Also skip the sampradaya label line if it slipped through
                body_lines = []
                for line in lines[start:]:
                    if line.strip() and BRAHMA_LABEL not in line:
                        body_lines.append(line)
                body = "\n".join(body_lines)
                return body if body else None
    return None


async def scrape_chapter(
    client: httpx.AsyncClient,
    chapter: int,
    on_verse=None,
) -> list[BgOrgVerse]:
    verse_count = CHAPTER_VERSE_COUNTS.get(chapter, 0)
    results: list[BgOrgVerse] = []

    for v in range(1, verse_count + 1):
        url = _verse_url(chapter, v)
        try:
            resp = await fetch(client, url)
        except Exception as e:
            print(f"  [bgorg] Failed BG {chapter}.{v}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        baladeva = _extract_baladeva(soup)

        # Extract verse label from page title/header
        title_td = soup.find("td", string=re.compile(r"Verse\s+\d+"))
        verse_label = str(v)

        verse = BgOrgVerse(
            chapter=chapter,
            verse_number=v,
            verse_label=verse_label,
            source_url=url,
            baladeva=baladeva,
        )
        results.append(verse)
        if on_verse:
            await on_verse(verse)

    return results


async def scrape_chapters(chapters: list[int], on_verse=None) -> list[BgOrgVerse]:
    all_verses: list[BgOrgVerse] = []
    async with make_client() as client:
        for chapter in chapters:
            print(f"Scraping bhagavad-gita.org Chapter {chapter}...")
            verses = await scrape_chapter(client, chapter, on_verse=on_verse)
            all_verses.extend(verses)
            print(f"  → {len(verses)} verses with Baladeva commentary")
    return all_verses
