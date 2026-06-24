from db.models.pipeline import PipelineRun, PipelineError, PipelineStatus, PipelineStage
from db.models.base import PyObjectId

from repos.mongo.base_mongo_repo import BaseMongoRepository


class PipelineRunRepository(BaseMongoRepository[PipelineRun]):
    collection_name = "PIPELINE_RUNS"
    model_class = PipelineRun

    async def find_by_book(
        self,
        book_id: PyObjectId,
    ) -> list[PipelineRun]:
        return await self.find_many(
            {"book_id": book_id},
            limit=100,
        )

    async def find_running(
        self,
    ) -> list[PipelineRun]:
        return await self.find_many(
            {"status": PipelineStatus.RUNNING.value},
            limit=20,
        )

    async def find_failed(
        self,
    ) -> list[PipelineRun]:
        return await self.find_many(
            {"status": PipelineStatus.FAILED.value},
            limit=100,
        )

    async def find_by_stage(
        self,
        stage: PipelineStage,
    ) -> list[PipelineRun]:
        return await self.find_many(
            {"current_stage": stage.value},
            limit=100,
        )

    async def find_by_status(
        self,
        status: PipelineStatus,
    ) -> list[PipelineRun]:
        return await self.find_many(
            {"status": status.value},
            limit=100,
        )


class PipelineErrorRepository(BaseMongoRepository[PipelineError]):
    collection_name = "PIPELINE_ERRORS"
    model_class = PipelineError

    async def find_by_run(
        self,
        pipeline_run_id: PyObjectId,
    ) -> list[PipelineError]:
        return await self.find_many(
            {"pipeline_run_id": pipeline_run_id},
            limit=500,
        )

    async def find_fatal(
        self,
        pipeline_run_id: PyObjectId,
    ) -> list[PipelineError]:
        return await self.find_many(
            {
                "pipeline_run_id": pipeline_run_id,
                "is_fatal": True,
            },
            limit=100,
        )

    async def find_by_stage(
        self,
        stage: PipelineStage,
    ) -> list[PipelineError]:
        return await self.find_many(
            {"stage": stage.value},
            limit=500,
        )
