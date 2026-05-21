from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, DateTime, Enum, ForeignKey, Index, Integer,
    Text, UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Acharya(str, PyEnum):
    PRABHUPADA = "prabhupada"
    VISHVANATHA = "vishvanatha"
    BALADEVA = "baladeva"


class Verse(Base):
    __tablename__ = "verses"

    id = Column(Integer, primary_key=True)
    chapter = Column(Integer, nullable=False)
    verse = Column(Integer, nullable=False)
    # Some verses have sub-numbers (e.g. 13-14), stored as range string
    verse_label = Column(Text, nullable=False)          # "1", "13-14"
    sanskrit = Column(Text)
    transliteration = Column(Text)
    word_for_word = Column(Text)
    translation = Column(Text)                          # Prabhupada's translation
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    commentaries = relationship("Commentary", back_populates="verse", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="verse", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("chapter", "verse_label", name="uq_chapter_verse"),
    )

    def __repr__(self) -> str:
        return f"<Verse BG {self.chapter}.{self.verse_label}>"


class Commentary(Base):
    __tablename__ = "commentaries"

    id = Column(Integer, primary_key=True)
    verse_id = Column(Integer, ForeignKey("verses.id", ondelete="CASCADE"), nullable=False)
    acharya = Column(Enum(Acharya), nullable=False)
    text = Column(Text, nullable=False)
    source_url = Column(Text)
    scraped_at = Column(DateTime, default=func.now())

    verse = relationship("Verse", back_populates="commentaries")

    __table_args__ = (
        UniqueConstraint("verse_id", "acharya", name="uq_verse_acharya"),
        Index("ix_commentaries_acharya", "acharya"),
    )

    def __repr__(self) -> str:
        return f"<Commentary {self.acharya} on verse_id={self.verse_id}>"


class Insight(Base):
    """AI-generated analysis for a verse across all available commentaries."""
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True)
    verse_id = Column(Integer, ForeignKey("verses.id", ondelete="CASCADE"), nullable=False)

    # Which acharyas were present when this insight was generated (comma-separated)
    acharyas_included = Column(Text, nullable=False)

    # Structured outputs from Claude (stored as JSON text)
    themes_json = Column(Text)          # list of {theme, description, acharyas[]}
    agreements_json = Column(Text)      # list of {point, acharyas[]}
    divergences_json = Column(Text)     # list of {point, positions: {acharya: stance}}
    synthesis = Column(Text)            # prose paragraph — unified philosophical insight

    model_used = Column(Text)
    generated_at = Column(DateTime, default=func.now())

    verse = relationship("Verse", back_populates="insights")

    __table_args__ = (
        Index("ix_insights_verse_id", "verse_id"),
    )
