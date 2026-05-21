"""Scraper for Prabhupada's Bhagavad-gita As It Is from vedabase.io."""
import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .base import fetch, make_client

BASE_URL = "https://vedabase.io/en/library/bg"


@dataclass
class ScrapedVerse:
    chapter: int
    verse_number: int
    verse_label: str          # "1" or "13-14" for ranges
    source_url: str
    sanskrit: Optional[str]
    transliteration: Optional[str]
    word_for_word: Optional[str]
    translation: Optional[str]
    purport: Optional[str]    # Prabhupada's commentary


def _clean(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return " ".join(text.split())


def _parse_verse_page(html: str, url: str, chapter: int, verse_number: int) -> ScrapedVerse:
    soup = BeautifulSoup(html, "lxml")

    def section_text(css_class: str) -> Optional[str]:
        el = soup.find(class_=css_class)
        if not el:
            return None
        # Remove the section heading h2 (e.g. "Devanagari", "Verse text")
        for h2 in el.find_all("h2"):
            h2.decompose()
        return _clean(el.get_text(separator=" "))

    # verse_label: extract from title e.g. "Bg. 2.13-14" → "13-14"
    title_el = soup.find("h1") or soup.find(class_="av-title")
    verse_label = str(verse_number)
    if title_el:
        title = title_el.get_text(strip=True)
        # Format: "Bg. 2.13-14" or "Bg. 2.13"
        parts = title.split(".")
        if len(parts) >= 3:
            verse_label = parts[-1].strip()

    # Collect all purport paragraphs under av-purport
    purport_text = None
    purport_el = soup.find(class_="av-purport")
    if purport_el:
        for h2 in purport_el.find_all("h2"):
            h2.decompose()
        paras = purport_el.find_all("p")
        if paras:
            purport_text = "\n\n".join(_clean(p.get_text()) for p in paras if p.get_text(strip=True))
        else:
            purport_text = _clean(purport_el.get_text(separator="\n\n"))

    return ScrapedVerse(
        chapter=chapter,
        verse_number=verse_number,
        verse_label=verse_label,
        source_url=url,
        sanskrit=section_text("av-devanagari"),
        transliteration=section_text("av-verse_text"),
        word_for_word=section_text("av-synonyms"),
        translation=section_text("av-translation"),
        purport=purport_text,
    )


async def get_chapter_verse_urls(client: httpx.AsyncClient, chapter: int) -> list[tuple[str, int]]:
    """Return list of (absolute_url, first_verse_number) from the chapter index page."""
    index_url = f"{BASE_URL}/{chapter}/"
    resp = await fetch(client, index_url)
    soup = BeautifulSoup(resp.text, "lxml")

    seen: set[str] = set()
    results: list[tuple[str, int]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Match /en/library/bg/{chapter}/{verse_label}/
        prefix = f"/en/library/bg/{chapter}/"
        if not href.startswith(prefix):
            continue
        label = href[len(prefix):].strip("/")
        if not label or label in seen:
            continue
        # Skip if label contains non-numeric/non-dash chars (e.g. chapter index itself)
        if not all(c.isdigit() or c == "-" for c in label):
            continue
        seen.add(label)
        first_verse = int(label.split("-")[0])
        results.append((f"https://vedabase.io{href}", first_verse))

    return sorted(results, key=lambda x: x[1])


async def scrape_chapter(
    client: httpx.AsyncClient,
    chapter: int,
    on_verse=None,
) -> list[ScrapedVerse]:
    """Scrape all verses for one chapter. Calls on_verse(verse) after each."""
    verse_urls = await get_chapter_verse_urls(client, chapter)
    results: list[ScrapedVerse] = []

    for url, verse_number in verse_urls:
        try:
            resp = await fetch(client, url)
        except Exception as e:
            print(f"  [!] Failed BG {chapter}.{verse_number}: {e}")
            continue

        verse = _parse_verse_page(resp.text, url, chapter, verse_number)
        results.append(verse)

        if on_verse:
            await on_verse(verse)

    return results


async def scrape_chapters(chapters: list[int], on_verse=None) -> list[ScrapedVerse]:
    all_verses: list[ScrapedVerse] = []
    async with make_client() as client:
        for chapter in chapters:
            print(f"Scraping Chapter {chapter}...")
            verses = await scrape_chapter(client, chapter, on_verse=on_verse)
            all_verses.extend(verses)
            print(f"  → {len(verses)} verses collected")
    return all_verses
