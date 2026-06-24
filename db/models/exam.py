from datetime import datetime
from typing import Optional

from pydantic import Field

from db.models.base import MongoBase, PyObjectId, istnow
from enum import Enum


class ExamStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    APPROVED = "approved"
    PUBLISHED = "published"


class DifficultyDistribution(MongoBase):
    """Embedded sub-document recording the easy/medium/hard breakdown
    for a generated exam.  Stored inside the Exam document."""

    easy: int = 0
    medium: int = 0
    hard: int = 0


class Exam(MongoBase):
    book_id: PyObjectId

    pipeline_run_id: Optional[PyObjectId] = None

    title: str

    chapter_ids: list[PyObjectId] = Field(default_factory=list)

    question_ids: list[PyObjectId] = Field(default_factory=list)

    difficulty_distribution: Optional[DifficultyDistribution] = None

    total_marks: int = 0

    question_count: int = 0

    duration_minutes: int

    status: ExamStatus = ExamStatus.GENERATED

    generator_version: Optional[str] = None

    output_pdf_path: str | None = None

    generated_at: datetime = Field(default_factory=istnow)
    created_at: datetime = Field(default_factory=istnow)

    class Settings:
        collection = "EXAMS"
        indexes = [
            [("book_id", 1)],
            [("pipeline_run_id", 1)],
            [("status", 1)],
        ]
