"""
MinIO storage service.

Extends the base upload/delete interface already present in the repo
with two additions needed by the ingestion pipeline:
  - ``ensure_bucket()`` — idempotent bucket creation
  - ``upload_page()``   — page PDF upload with structured metadata

The original ``upload_file`` / ``get_url`` / ``delete`` signatures are
preserved exactly so existing callers are unaffected.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from minio import Minio
from minio.error import S3Error

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)


class MinioStorageService:
    def __init__(self) -> None:
        settings = get_settings()

        self.bucket = settings.minio_bucket
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    # ------------------------------------------------------------------
    # Existing interface (unchanged)
    # ------------------------------------------------------------------

    def upload_file(
        self,
        file_path: Path,
        object_key: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        if object_key is None:
            object_key = f"{uuid4()}_{file_path.name}"

        self.client.fput_object(
            self.bucket,
            object_key,
            str(file_path),
            content_type=content_type,
        )
        return object_key

    def get_url(self, object_key: str) -> str:
        return f"http://{get_settings().minio_endpoint}/{self.bucket}/{object_key}"

    def delete(self, object_key: str) -> None:
        self.client.remove_object(self.bucket, object_key)

    # ------------------------------------------------------------------
    # New: ingestion helpers
    # ------------------------------------------------------------------

    def ensure_bucket(self) -> None:
        """Create the configured bucket if it does not already exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info("bucket_created", bucket=self.bucket)
            else:
                logger.debug("bucket_exists", bucket=self.bucket)
        except S3Error as exc:
            logger.error("bucket_ensure_failed", bucket=self.bucket, error=str(exc))
            raise

    def upload_page(
        self,
        file_path: Path,
        book_id: str,
        page_number: int,
        object_key: str | None = None,
        extra_metadata: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        """
        Upload a single-page PDF produced by PDFExtractorService.

        Args:
            file_path:      Local path to the single-page PDF.
            book_id:        String form of the book's MongoDB _id.
            page_number:    1-based page number (used in the object key).
            object_key:     Override the generated object key.
            extra_metadata: Additional string metadata attached to the object.

        Returns:
            ``(object_key, etag)`` tuple.

        Raises:
            FileNotFoundError: If *file_path* does not exist.
            S3Error:           On upload failure.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Page PDF not found: {file_path}")

        if object_key is None:
            object_key = f"pages/{book_id}/page_{page_number:03d}.pdf"

        metadata: dict[str, str] = {
            "book-id": book_id,
            "page-number": str(page_number),
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        try:
            result = self.client.fput_object(
                self.bucket,
                object_key,
                str(file_path),
                content_type="application/pdf",
                metadata=metadata,
            )
        except S3Error as exc:
            logger.error(
                "page_upload_failed",
                object_key=object_key,
                error=str(exc),
            )
            raise

        logger.info(
            "page_uploaded",
            object_key=object_key,
            size_bytes=file_path.stat().st_size,
            etag=result.etag,
        )
        return object_key, result.etag

    def object_exists(self, object_key: str) -> bool:
        """Return True if *object_key* already exists in the bucket."""
        try:
            self.client.stat_object(self.bucket, object_key)
            return True
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                return False
            raise
