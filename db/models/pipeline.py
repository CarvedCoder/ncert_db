from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import Field
from db.models.base import MongoBase, PyObjectId, istnow


class PipelineStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class PipelineStage(str, Enum):
    PDF_PROCESSOR = "pdf_processor"
    QUESTION_PLANNER = "question_planner"
    QUESTION_GENERATOR = "question_generator"
    EXAM_FORMATTER = "exam_formatter"


class PipelineRun(MongoBase):
    book_id: PyObjectId

    status: PipelineStatus = PipelineStatus.QUEUED

    current_stage: PipelineStage | None = None

    pipeline_version: str | None = None

    total_pages: int = 0
    processed_pages: int = 0

    total_chunks: Optional[int] = 0
    total_concepts: Optional[int] = 0

    total_questions_generated: int = 0
    total_exams_generated: int = 0

    started_at: datetime | None = None
    completed_at: datetime | None = None

    created_at: datetime = Field(default_factory=istnow)

    class Settings:
        collection = "PIPELINE_RUNS"
        indexes = [
            [("book_id", 1)],
            [("status", 1)],
            [("created_at", -1)],
        ]


class PipelineError(MongoBase):
    """Records failures that occur during post-ingestion pipeline stages:
    question planning, generation, validation, exam formatting, and export.

    Separate from IngestionError so ingestion and generation failures
    can be monitored and retried independently.
    """

    pipeline_run_id: PyObjectId

    stage: PipelineStage

    error_code: str

    error_message: Optional[str] = None

    component: Optional[str] = None

    input_reference: Optional[str] = None

    retry_count: int = 0

    is_fatal: bool = False

    stack_trace: Optional[str] = None

    created_at: datetime = Field(default_factory=istnow)

    class Settings:
        collection = "PIPELINE_ERRORS"
        indexes = [
            [("pipeline_run_id", 1)],
            [("pipeline_run_id", 1), ("stage", 1)],
            [("is_fatal", 1)],
        ]
