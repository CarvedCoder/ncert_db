from db.models.base import PyObjectId
from db.models.media_asset import (
    MediaAsset,
    ObjectType,
)

from repos.mongo.base_mongo_repo import BaseMongoRepository


class MediaAssetRepository(BaseMongoRepository[MediaAsset]):
    collection_name = "OBJECTS"
    model_class = MediaAsset

    async def find_by_book(
        self,
        book_id: PyObjectId,
    ) -> list[MediaAsset]:
        return await self.find_many(
            {"book_id": book_id},
            limit=10000,
        )

    async def find_by_chapter(
        self,
        chapter_id: PyObjectId,
    ) -> list[MediaAsset]:
        return await self.find_many(
            {"chapter_id": chapter_id},
            limit=10000,
        )

    async def find_by_type(
        self,
        object_type: ObjectType,
    ) -> list[MediaAsset]:
        return await self.find_many(
            {
                "object_type": object_type.value,
            },
            limit=10000,
        )

    async def find_page_images(
        self,
        chapter_id: PyObjectId,
    ) -> list[MediaAsset]:
        return await self.find_many(
            {
                "chapter_id": chapter_id,
                "object_type": ObjectType.PAGE_IMAGE.value,
            },
            limit=5000,
        )

    async def find_source_pdf(
        self,
        book_id: PyObjectId,
    ) -> MediaAsset | None:
        docs = await self.find_many(
            {
                "book_id": book_id,
                "object_type": ObjectType.PDF.value,
            },
            limit=1,
        )

        return docs[0] if docs else None
