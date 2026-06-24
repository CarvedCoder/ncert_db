from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from db.models.base import (
    MongoBase,
    PyObjectId,
    istnow,
)


class ObjectType(str, Enum):
    PAGE_IMAGE = "PAGE_IMAGE"
    PDF = "PDF"
    FIGURE = "FIGURE"
    EXPORT = "EXPORT"
    SNAPSHOT = "SNAPSHOT"


class MediaAsset(MongoBase):
    book_id: PyObjectId

    chapter_id: Optional[PyObjectId] = None

    object_type: ObjectType

    object_key: str

    bucket_name: str

    object_url: Optional[str] = None

    page_no: Optional[int] = None

    mime_type: str

    size_bytes: int

    etag: Optional[str] = None

    metadata: dict = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=istnow)

    class Settings:
        collection = "OBJECTS"

        indexes = [
            [("book_id", 1)],
            [("chapter_id", 1)],
            [("object_type", 1)],
            [("page_no", 1)],
            [("created_at", -1)],
            [
                ("book_id", 1),
                ("chapter_id", 1),
                ("object_type", 1),
            ],
        ]
