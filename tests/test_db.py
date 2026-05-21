import sys
import pytest

sys.path.insert(0, ".")

from db.session import init_db, AsyncSessionLocal
from db.crud import upsert_verse, upsert_commentary, get_verse_with_all
from db.models import Acharya


async def test_verse_and_commentary_roundtrip():
    await init_db()
    async with AsyncSessionLocal() as session:
        verse = await upsert_verse(
            session,
            chapter=1,
            verse=1,
            verse_label="1",
            sanskrit="धृतराष्ट्र उवाच",
            translation="Dhritarashtra said...",
        )
        await upsert_commentary(
            session,
            verse_id=verse.id,
            acharya=Acharya.PRABHUPADA,
            text="Sanjaya said: O King, after looking over the army...",
            source_url="https://vedabase.io/en/library/bg/1/1/",
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        loaded = await get_verse_with_all(session, chapter=1, verse_label="1")
        assert loaded is not None
        assert loaded.chapter == 1
        assert len(loaded.commentaries) == 1
        assert loaded.commentaries[0].acharya == Acharya.PRABHUPADA
