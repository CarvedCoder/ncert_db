from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import Field
from db.models.base import MongoBase, istnow


class Book(MongoBase):
    class_no: int
    subject: str
    title: str
    edition: Optional[str] = None
    academic_year: Optional[str] = None
    total_pages: Optional[int] = None
    created_at: datetime = Field(default_factory=istnow)
    updated_at: datetime = Field(default_factory=istnow)

    class Settings:
        collection = "BOOKS"
        indexes = [
            [("class_no", 1), ("subject", 1), ("title", 1)],
        ]
