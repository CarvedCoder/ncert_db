from db.models.base import PyObjectId
from db.models.extracted_page import ExtractedPage
from repos.mongo.base_mongo_repo import BaseMongoRepository


class ExtractedPageRepository(BaseMongoRepository[ExtractedPage]):
    collection_name = "EXTRACTED_PAGES"
    model_class = ExtractedPage

    async def find_by_book(
        self,
        book_id: PyObjectId,
    ) -> list[ExtractedPage]:
        return await self.find_many(
            {"book_id": book_id},
            limit=10000,
        )

    async def find_by_chapter(
        self,
        chapter_id: PyObjectId,
    ) -> list[ExtractedPage]:
        return await self.find_many(
            {"chapter_id": chapter_id},
            limit=5000,
        )

    async def find_by_page_number(
        self,
        book_id: PyObjectId,
        page_number: int,
    ) -> ExtractedPage | None:
        results = await self.find_many(
            {
                "book_id": book_id,
                "page_number": page_number,
            },
            limit=1,
        )
        return results[0] if results else None

    async def find_unlinked_pages(
        self,
        book_id: PyObjectId,
    ) -> list[ExtractedPage]:
        """Return pages that have not yet been assigned a chapter."""
        return await self.find_many(
            {
                "book_id": book_id,
                "chapter_id": None,
            },
            limit=10000,
        )
