from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import Field
from db.models.base import MongoBase, PyObjectId, istnow


class Chapter(MongoBase):
    book_id: PyObjectId
    chapter_no: int
    title: str
    summary: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    created_at: datetime = Field(default_factory=istnow)
    updated_at: datetime = Field(default_factory=istnow)

    class Settings:
        collection = "CHAPTERS"
        indexes = [
            [("book_id", 1), ("chapter_no", 1)],
        ]
