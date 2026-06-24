from db.models.exam import Exam, ExamStatus
from db.models.base import PyObjectId
from repos.mongo.base_mongo_repo import BaseMongoRepository


class ExamRepository(BaseMongoRepository[Exam]):
    collection_name = "EXAMS"
    model_class = Exam

    async def find_by_book(
        self,
        book_id: PyObjectId,
    ) -> list[Exam]:
        return await self.find_many(
            {"book_id": book_id},
            limit=100,
        )

    async def find_by_status(
        self,
        status: ExamStatus,
    ) -> list[Exam]:
        return await self.find_many(
            {"status": status.value},
            limit=100,
        )

    async def find_latest_by_book(
        self,
        book_id: PyObjectId,
    ) -> Exam | None:

        raw = await (
            self._col.find({"book_id": book_id})
            .sort("created_at", -1)
            .limit(1)
            .to_list(1)
        )

        return self._deserialise(raw[0]) if raw else None

    async def find_by_pipeline_run(
        self,
        pipeline_run_id: PyObjectId,
    ) -> list[Exam]:
        return await self.find_many(
            {"pipeline_run_id": pipeline_run_id},
            limit=100,
        )
