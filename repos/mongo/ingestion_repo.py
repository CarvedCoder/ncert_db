from db.models.base import PyObjectId
from db.models.ingestion import IngestionJob, IngestionError, IngestionStatus


from repos.mongo.base_mongo_repo import BaseMongoRepository


class IngestionJobRepository(BaseMongoRepository[IngestionJob]):
    collection_name = "INGESTION_JOBS"
    model_class = IngestionJob

    async def find_by_book(
        self,
        book_id: PyObjectId,
    ) -> list[IngestionJob]:
        return await self.find_many(
            {"book_id": book_id},
            limit=50,
        )

    async def find_running(
        self,
    ) -> list[IngestionJob]:
        return await self.find_many(
            {"status": IngestionStatus.RUNNING.value},
            limit=20,
        )

    async def increment_counters(
        self,
        job_id: PyObjectId,
        **counters: int,
    ) -> None:

        payload = {k: v for k, v in counters.items() if v}

        if not payload:
            return

        await self._col.update_one(
            {"_id": job_id},
            {"$inc": payload},
        )


class IngestionErrorRepository(BaseMongoRepository[IngestionError]):
    collection_name = "INGESTION_ERRORS"
    model_class = IngestionError

    async def find_by_job(
        self,
        job_id: PyObjectId,
    ) -> list[IngestionError]:
        return await self.find_many(
            {"ingestion_job_id": job_id},
            limit=500,
        )

    async def find_fatal(
        self,
        job_id: PyObjectId,
    ) -> list[IngestionError]:
        return await self.find_many(
            {
                "ingestion_job_id": job_id,
                "is_fatal": True,
            },
            limit=100,
        )
