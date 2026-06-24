from db.models.book import Book
from db.models.chapter import Chapter
from db.models.exam import Exam
from db.models.pipeline import PipelineRun, PipelineError
from db.models.ingestion import IngestionJob, IngestionError
from db.models.media_asset import MediaAsset
from db.models.ocr import Ocr
from repos.mongo.client import get_database

MODELS = [
    Book,
    Chapter,
    Exam,
    PipelineRun,
    PipelineError,
    IngestionError,
    IngestionJob,
]


async def create_indexes():
    db = get_database()

    for model in MODELS:
        collection = db[model.Settings.collection]

        for index in model.Settings.indexes:
            await collection.create_index(index)
