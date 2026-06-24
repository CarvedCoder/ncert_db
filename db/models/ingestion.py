from __future__ import annotations
from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import Field
from db.models.base import MongoBase, PyObjectId, istnow


class IngestionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class IngestionStage(str, Enum):
    PDF_PARSE = "pdf_parse"
    MEDIA_EXTRACT = "media_extract"


class IngestionJob(MongoBase):
    book_id: PyObjectId
    status: IngestionStatus = IngestionStatus.QUEUED
    pipeline_version: Optional[str] = None
    pdf_parsed: int = 0
    images_extracted: int = 0
    error_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=istnow)

    class Settings:
        collection = "INGESTION_JOBS"
        indexes = [
            [("book_id", 1)],
            [("status", 1)],
            [("book_id", 1), ("status", 1)],
        ]


class IngestionError(MongoBase):
    ingestion_job_id: PyObjectId
    stage: IngestionStage
    error_code: str
    error_message: Optional[str] = None
    page_no: Optional[int] = None
    stack_trace: Optional[str] = None
    is_fatal: bool = False
    created_at: datetime = Field(default_factory=istnow)

    class Settings:
        collection = "INGESTION_ERRORS"
        indexes = [
            [("ingestion_job_id", 1)],
            [("ingestion_job_id", 1), ("stage", 1)],
            [("is_fatal", 1)],
        ]
