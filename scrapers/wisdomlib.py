"""Scraper for Vishvanatha Chakravarti's Sarartha-Varsini Tika from wisdomlib.org."""
import re
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .base import fetch, make_client

BASE_URL = "https://www.wisdomlib.org"
TOC_URL = f"{BASE_URL}/hinduism/book/shrimad-bhagavad-gita"


@dataclass
class WisdomlibVerse:
    chapter: int
    verse_label: str        # e.g. "1", "4-6"
    source_url: str
    vishvanatha: Optional[str]


def _parse_chapter_verse(title: str) -> tuple[int, str]:
    """Parse 'Verse 2.47' or 'Verses 1.4-6' → (2, '47') or (1, '4-6')."""
    m = re.search(r"(\d+)\.(\d[\d\-]*)", title)
    if m:
        return int(m.group(1)), m.group(2)
    return 0, "0"


def _extract_commentary(soup: BeautifulSoup, heading_text: str) -> Optional[str]:
    """Extract all paragraphs under a given h2 heading."""
    h2 = soup.find("h2", string=lambda s: s and heading_text in s)
    if not h2:
        return None
    paragraphs = []
    for sib in h2.find_next_siblings():
        if sib.name == "h2":
            break
        if sib.name == "p":
            text = sib.get_text(separator=" ", strip=True)
            # Skip the attribution line "(By Srila Vishvanatha...)"
            if text.startswith("(By "):
                continue
            if text:
                paragraphs.append(text)
    return "\n\n".join(paragraphs) if paragraphs else None


async def fetch_chapter_verse_urls(
    client: httpx.AsyncClient, chapter: int
) -> list[tuple[str, str]]:
    """Return (absolute_url, verse_label) for all verse pages in a chapter.

    Filters by link text (e.g. 'Verse 1.3', 'Verses 1.4-6') so we only
    fetch the pages we actually need — no scanning all 678 docs.
    """
    resp = await fetch(client, TOC_URL)
    soup = BeautifulSoup(resp.text, "lxml")

    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    pattern = re.compile(rf"Verses?\s+{chapter}\.(\d[\d\-]*)", re.IGNORECASE)

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/shrimad-bhagavad-gita/d/doc" not in href:
            continue
        link_text = a.get_text(strip=True)
        m = pattern.match(link_text)
        if not m or href in seen:
            continue
        seen.add(href)
        verse_label = m.group(1)
        url = BASE_URL + href if href.startswith("/") else href
        results.append((url, verse_label))

    return results


async def scrape_chapter(
    client: httpx.AsyncClient,
    chapter: int,
    on_verse=None,
) -> list[WisdomlibVerse]:
    verse_urls = await fetch_chapter_verse_urls(client, chapter)
    results: list[WisdomlibVerse] = []

    for url, verse_label in verse_urls:
        try:
            resp = await fetch(client, url)
        except Exception as e:
            print(f"  [wisdomlib] Failed BG {chapter}.{verse_label}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        vishvanatha = _extract_commentary(soup, "Sārārtha-Varṣiṇī Ṭīkā")
        if not vishvanatha:
            continue

        verse = WisdomlibVerse(
            chapter=chapter,
            verse_label=verse_label,
            source_url=url,
            vishvanatha=vishvanatha,
        )
        results.append(verse)
        if on_verse:
            await on_verse(verse)

    return results


async def scrape_chapters(
    chapters: list[int], on_verse=None
) -> list[WisdomlibVerse]:
    all_verses: list[WisdomlibVerse] = []
    async with make_client() as client:
        for chapter in chapters:
            print(f"Scraping Wisdomlib Chapter {chapter}...")
            verses = await scrape_chapter(client, chapter, on_verse=on_verse)
            all_verses.extend(verses)
            print(f"  → {len(verses)} verses with Vishvanatha commentary")
    return all_verses
