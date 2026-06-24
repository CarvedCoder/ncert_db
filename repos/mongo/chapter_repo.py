from db.models.chapter import Chapter
from db.models.base import PyObjectId
from repos.mongo.base_mongo_repo import BaseMongoRepository


class ChapterRepository(BaseMongoRepository[Chapter]):
    collection_name = "CHAPTERS"
    model_class = Chapter

    async def find_by_book(
        self,
        book_id: PyObjectId,
    ) -> list[Chapter]:
        return await self.find_many(
            {"book_id": book_id},
            limit=200,
        )

    async def find_by_book_and_chapter_no(
        self,
        book_id: PyObjectId,
        chapter_no: int,
    ) -> Chapter | None:
        results = await self.find_many(
            {
                "book_id": book_id,
                "chapter_no": chapter_no,
            },
            limit=1,
        )

        return results[0] if results else None

    async def find_or_create(
        self,
        chapter: Chapter,
    ) -> tuple[PyObjectId, bool]:

        existing = await self.find_by_book_and_chapter_no(
            chapter.book_id,
            chapter.chapter_no,
        )

        if existing and existing.id:
            return existing.id, False

        chapter_id = await self.insert(chapter)
        return chapter_id, True
