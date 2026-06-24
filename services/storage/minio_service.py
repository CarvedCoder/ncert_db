from pathlib import Path
from uuid import uuid4

from minio import Minio

from core.config import get_settings


class MinioStorageService:
    def __init__(self):
        settings = get_settings()

        self.bucket = settings.minio_bucket

        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def upload_file(
        self,
        file_path: Path,
        object_key: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> str:

        file_path = file_path

        if object_key is None:
            object_key = f"{uuid4()}_{file_path.name}"

        self.client.fput_object(
            self.bucket,
            object_key,
            str(file_path),
            content_type=content_type,
        )

        return object_key

    def get_url(
        self,
        object_key: str,
    ) -> str:

        return f"http://{get_settings().minio_endpoint}/{self.bucket}/{object_key}"

    def delete(
        self,
        object_key: str,
    ):
        self.client.remove_object(
            self.bucket,
            object_key,
        )
