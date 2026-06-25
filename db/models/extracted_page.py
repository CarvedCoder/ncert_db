from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from db.models.base import MongoBase, PyObjectId, istnow


class ExtractedPage(MongoBase):
    """
    Represents a single extracted page from an NCERT PDF.

    Persisted to MongoDB; the actual single-page PDF lives in MinIO
    and is referenced via the corresponding MediaAsset.
    """

    book_id: PyObjectId
    chapter_id: Optional[PyObjectId] = None

    page_number: int
    total_pages: int

    # Text extracted by PyMuPDF (may be empty for scanned pages)
    text_content: Optional[str] = None
    word_count: Optional[int] = None
    has_images: bool = False

    page_width: Optional[float] = None
    page_height: Optional[float] = None

    # MinIO object key for the single-page PDF (populated after upload)
    object_key: Optional[str] = None

    created_at: datetime = Field(default_factory=istnow)
    updated_at: datetime = Field(default_factory=istnow)

    class Settings:
        collection = "EXTRACTED_PAGES"

        indexes = [
            [("book_id", 1), ("page_number", 1)],
            [("book_id", 1), ("chapter_id", 1)],
            [("chapter_id", 1)],
            [("created_at", -1)],
        ]
