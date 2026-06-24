"""
db/models/ocr_chunk.py

Permanent storage model for OCR_CHUNKS collection.
Each record represents one LangChain-produced text chunk from a single PDF page.
This is the final source of truth after ExtractedPage records are deleted.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum


from pydantic import Field

from db.models.base import MongoBase, PyObjectId, istnow


class ExtractionMethod(str, Enum):
    PYMUPDF = "pymupdf"
    SURYA_OCR = "surya_ocr"
    PYMUPDF_SURYA_HYBRID = "pymupdf_surya_hybrid"


class Ocr(MongoBase):
    """
    Permanent content chunk produced by the OCR ingestion pipeline.

    Lifecycle:
        PDF → ExtractedPage (temporary) → OcrChunk (permanent) → delete ExtractedPage
    """

    book_id: PyObjectId
    chapter_id: PyObjectId
    media_asset_id: PyObjectId

    page_no: int

    text: str
    token_count: int

    extraction_method: ExtractionMethod

    contains_math: bool = False
    contains_table: bool = False
    contains_figure_caption: bool = False

    created_at: datetime = Field(default_factory=istnow)

    class Settings:
        collection = "OCR_CHUNKS"

        indexes = [
            [("book_id", 1)],
            [("chapter_id", 1)],
            [("media_asset_id", 1)],
            [("page_no", 1)],
            [("book_id", 1), ("chapter_id", 1)],
            [("book_id", 1), ("chapter_id", 1), ("page_no", 1)],
        ]
