"""
repos/mongo/ocr_repo.py

Repository for the OCR collection.
"""

from __future__ import annotations

from db.models.base import PyObjectId
from db.models.ocr import Ocr
from repos.mongo.base_mongo_repo import BaseMongoRepository


class OcrChunkRepository(BaseMongoRepository[Ocr]):
    collection_name = "OCR_CHUNKS"
    model_class = Ocr

    async def find_by_chapter(
        self,
        chapter_id: PyObjectId,
    ) -> list[Ocr]:
        """Return all chunks for a chapter, ordered by page → chunk_index."""
        return await self.find_many(
            {"chapter_id": chapter_id},
            limit=100_000,
        )

    async def find_by_page(
        self,
        chapter_id: PyObjectId,
        page_no: int,
    ) -> list[Ocr]:
        return await self.find_many(
            {"chapter_id": chapter_id, "page_no": page_no},
            limit=1_000,
        )

    async def find_by_media_asset(
        self,
        media_asset_id: PyObjectId,
    ) -> list[Ocr]:
        return await self.find_many(
            {"media_asset_id": media_asset_id},
            limit=100_000,
        )

    async def delete_by_chapter(self, chapter_id: PyObjectId) -> int:
        """
        Bulk-delete all for a chapter.
        Returns deleted count. Used when re-ingesting.
        """
        try:
            result = await self._col.delete_many({"chapter_id": chapter_id})
            return result.deleted_count
        except Exception as exc:
            from core.exceptions import RepositoryError

            raise RepositoryError(f"delete_by_chapter failed: {exc}") from exc

    async def count_by_chapter(self, chapter_id: PyObjectId) -> int:
        return await self.count({"chapter_id": chapter_id})
