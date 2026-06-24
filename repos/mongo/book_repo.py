from db.models.book import Book
from repos.mongo.base_mongo_repo import BaseMongoRepository


class BookRepository(BaseMongoRepository[Book]):
    collection_name = "BOOKS"
    model_class = Book

    async def find_by_class_and_subject(
        self,
        class_no: int,
        subject: str,
        edition: str | None = None,
    ) -> Book | None:
        filter_ = {
            "class_no": class_no,
            "subject": subject,
        }

        if edition is not None:
            filter_["edition"] = edition

        results = await self.find_many(
            filter_,
            limit=1,
        )

        return results[0] if results else None

    async def find_by_class(
        self,
        class_no: int,
    ) -> list[Book]:
        return await self.find_many(
            {"class_no": class_no},
            limit=100,
        )

    async def find_by_subject(
        self,
        subject: str,
    ) -> list[Book]:
        return await self.find_many(
            {"subject": subject},
            limit=100,
        )
