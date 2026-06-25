"""
PDF ingestion service.

Orchestrates the end-to-end flow for a single NCERT book:
  1. Create / resolve a Book document in MongoDB.
  2. Extract pages via PDFExtractorService.
  3. Upload each single-page PDF to MinIO.
  4. Persist an ExtractedPage document per page (with object_key backfilled).
  5. Optionally persist a source-PDF MediaAsset for the whole book.

Follows the project's service layer conventions:
  - Async-first (Motor).
  - Uses get_logger() from core.logging.
  - Raises core.exceptions.IngestionError on unrecoverable failures.
  - No standalone retry decorator; callers may wrap with tenacity if needed.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from datetime import datetime, timezone

from core.exceptions import IngestionError
from core.logging import get_logger
from db.models.base import PyObjectId
from db.models.book import Book
from db.models.extracted_page import ExtractedPage
from db.models.media_asset import MediaAsset, ObjectType
from repos.mongo.book_repo import BookRepository
from repos.mongo.extracted_page_repo import ExtractedPageRepository
from repos.mongo.media_asset_repo import MediaAssetRepository
from services.pdf.pdf_extractor import PDFExtractorService
from services.storage.minio_service import MinioStorageService

logger = get_logger(__name__)


class IngestionService:
    """
    Stateless ingestion orchestrator.  Safe to instantiate once and call
    ``ingest_book()`` multiple times (e.g., from a CLI script or a task
    queue worker).
    """

    def __init__(
        self,
        book_repo: BookRepository | None = None,
        page_repo: ExtractedPageRepository | None = None,
        asset_repo: MediaAssetRepository | None = None,
        extractor: PDFExtractorService | None = None,
        storage: MinioStorageService | None = None,
    ) -> None:
        self._book_repo = book_repo or BookRepository()
        self._page_repo = page_repo or ExtractedPageRepository()
        self._asset_repo = asset_repo or MediaAssetRepository()
        self._extractor = extractor or PDFExtractorService()
        self._storage = storage or MinioStorageService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ingest_book(
        self,
        pdf_path: str | Path,
        class_no: int,
        subject: str,
        title: str,
        edition: str | None = None,
        academic_year: str | None = None,
        chapter_id: PyObjectId | None = None,
        skip_existing: bool = True,
    ) -> dict:
        """
        Ingest a single NCERT PDF.

        Args:
            pdf_path:      Path to the source PDF.
            class_no:      NCERT class number (e.g., 8).
            subject:       Subject string (e.g., "Science").
            title:         Full book title.
            edition:       Optional edition string.
            academic_year: Optional academic year string.
            chapter_id:    Optional chapter to associate all pages with.
            skip_existing: If True, skip pages whose object_key already
                           exists in MinIO (idempotent re-runs).

        Returns:
            Summary dict with keys: book_id, total_pages, uploaded,
            skipped, failed.
        """
        pdf_path = Path(pdf_path)

        # 1. Ensure MinIO bucket exists
        self._storage.ensure_bucket()

        # 2. Resolve or create Book
        book_id = await self._resolve_book(
            class_no=class_no,
            subject=subject,
            title=title,
            edition=edition,
            academic_year=academic_year,
        )

        logger.info(
            "ingestion_started",
            book_id=str(book_id),
            pdf=str(pdf_path),
        )

        # 3. Extract pages (CPU-bound, run in executor to not block the loop)
        loop = asyncio.get_event_loop()
        page_pairs = await loop.run_in_executor(
            None,
            lambda: self._extractor.extract(
                pdf_path=pdf_path,
                book_id=book_id,
                chapter_id=chapter_id,
            ),
        )

        # 4. Upload & persist
        uploaded = skipped = failed = 0

        for extracted_page, page_path in page_pairs:
            object_key = f"pages/{book_id}/page_{extracted_page.page_number:03d}.pdf"

            if skip_existing and self._storage.object_exists(object_key):
                logger.debug(
                    "page_skipped_exists",
                    object_key=object_key,
                )
                skipped += 1
                continue

            try:
                key, etag = self._storage.upload_page(
                    file_path=page_path,
                    book_id=str(book_id),
                    page_number=extracted_page.page_number,
                    object_key=object_key,
                )
            except Exception as exc:
                logger.error(
                    "page_upload_error",
                    page_no=extracted_page.page_number,
                    error=str(exc),
                )
                failed += 1
                continue

            # Backfill object_key and persist
            extracted_page.object_key = key
            extracted_page.book_id = book_id

            try:
                await self._page_repo.insert(extracted_page)
            except Exception as exc:
                logger.error(
                    "page_persist_error",
                    page_no=extracted_page.page_number,
                    error=str(exc),
                )
                # Don't abort the entire run for a DB write failure
                failed += 1
                continue

            uploaded += 1

        # 5. Persist a PDF MediaAsset for the source file
        await self._record_source_asset(
            pdf_path=pdf_path,
            book_id=book_id,
        )

        # 6. Update book's total_pages
        await self._book_repo.update(
            book_id,
            {"total_pages": len(page_pairs)},
        )

        summary = {
            "book_id": str(book_id),
            "total_pages": len(page_pairs),
            "uploaded": uploaded,
            "skipped": skipped,
            "failed": failed,
        }

        logger.info("ingestion_complete", **summary)
        return summary

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _resolve_book(
        self,
        class_no: int,
        subject: str,
        title: str,
        edition: str | None,
        academic_year: str | None,
    ) -> PyObjectId:
        existing = await self._book_repo.find_by_class_and_subject(
            class_no=class_no,
            subject=subject,
            edition=edition,
        )
        if existing and existing.id:
            logger.debug("book_resolved", book_id=str(existing.id))
            return existing.id

        book = Book(
            class_no=class_no,
            subject=subject,
            title=title,
            edition=edition,
            academic_year=academic_year,
        )
        book_id = await self._book_repo.insert(book)
        logger.info("book_created", book_id=str(book_id), title=title)
        return book_id

    async def _record_source_asset(
        self,
        pdf_path: Path,
        book_id: PyObjectId,
    ) -> None:
        """Persist a MediaAsset record for the original source PDF if not present."""
        existing = await self._asset_repo.find_source_pdf(book_id)
        if existing:
            return

        try:
            object_key = self._storage.upload_file(
                file_path=pdf_path,
                object_key=f"sources/{book_id}/{pdf_path.name}",
                content_type="application/pdf",
            )
            from core.config import get_settings

            settings = get_settings()

            asset = MediaAsset(
                book_id=book_id,
                object_type=ObjectType.PDF,
                object_key=object_key,
                bucket_name=settings.minio_bucket,
                object_url=self._storage.get_url(object_key),
                mime_type="application/pdf",
                size_bytes=pdf_path.stat().st_size,
                metadata={"source": "ingestion_pipeline"},
            )
            await self._asset_repo.insert(asset)
            logger.info("source_asset_recorded", object_key=object_key)
        except Exception as exc:
            # Non-fatal: log and continue
            logger.warning("source_asset_failed", error=str(exc))
