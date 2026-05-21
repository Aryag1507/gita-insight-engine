"""Pydantic response schemas for the API."""
import json
from typing import Optional
from pydantic import BaseModel, model_validator


class CommentaryOut(BaseModel):
    acharya: str
    text: str
    source_url: Optional[str] = None

    class Config:
        from_attributes = True


class Theme(BaseModel):
    theme: str
    description: str
    acharyas: list[str]


class Agreement(BaseModel):
    point: str
    acharyas: list[str]


class Divergence(BaseModel):
    point: str
    positions: dict[str, str]


class InsightOut(BaseModel):
    acharyas_included: list[str]
    themes: list[Theme]
    agreements: list[Agreement]
    divergences: list[Divergence]
    synthesis: Optional[str] = None
    model_used: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data):
        """ORM rows store JSON as strings — parse them before validation."""
        if hasattr(data, "__dict__"):
            # SQLAlchemy model instance
            d = {
                "acharyas_included": (data.acharyas_included or "").split(","),
                "themes": json.loads(data.themes_json or "[]"),
                "agreements": json.loads(data.agreements_json or "[]"),
                "divergences": json.loads(data.divergences_json or "[]"),
                "synthesis": data.synthesis,
                "model_used": data.model_used,
            }
            return d
        return data


class VerseOut(BaseModel):
    chapter: int
    verse_label: str
    sanskrit: Optional[str] = None
    transliteration: Optional[str] = None
    word_for_word: Optional[str] = None
    translation: Optional[str] = None

    class Config:
        from_attributes = True


class VerseDetailOut(VerseOut):
    commentaries: list[CommentaryOut] = []
    insight: Optional[InsightOut] = None


class SearchResult(BaseModel):
    chapter: int
    verse_label: str
    translation: Optional[str] = None
    matched_acharya: str
    snippet: str
