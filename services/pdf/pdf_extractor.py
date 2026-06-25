"""
PDF extraction service using PyMuPDF (fitz).

Handles page-wise splitting of NCERT PDFs and returns structured
ExtractedPage documents ready for persistence and MinIO upload.
Follows the service layer conventions of the ncert_db project:
  - Uses get_logger() from core.logging
  - Works with Pydantic db.models directly (no separate dataclass)
  - Raises core.exceptions.IngestionError on failure
"""

from __future__ import annotations

import fitz  # PyMuPDF
from pathlib import Path

from core.exceptions import IngestionError
from core.logging import get_logger
from db.models.extracted_page import ExtractedPage
from db.models.base import PyObjectId

logger = get_logger(__name__)


class PDFExtractorService:
    """
    Splits a PDF into single-page PDFs and constructs ExtractedPage
    documents.  Purely I/O-bound; no DB or MinIO interaction.

    Args:
        scratch_dir: Temporary directory for single-page PDFs.
                     Defaults to ``./media_assets/pages``.
    """

    def __init__(self, scratch_dir: str | Path | None = None) -> None:
        from core.config import get_settings

        self._scratch = Path(
            scratch_dir or get_settings().media_storage_path
        ) / "pages"
        self._scratch.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        pdf_path: str | Path,
        book_id: PyObjectId,
        chapter_id: PyObjectId | None = None,
    ) -> list[tuple[ExtractedPage, Path]]:
        """
        Split *pdf_path* into individual single-page PDFs.

        Returns a list of ``(ExtractedPage, page_pdf_path)`` tuples —
        one per page.  The ExtractedPage instances are *not* persisted
        here; that is the responsibility of the caller (IngestionService).

        ``object_key`` is left ``None`` and must be filled in after the
        MinIO upload.

        Raises:
            IngestionError: If the PDF cannot be opened or a page cannot
                            be extracted.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise IngestionError(
                f"PDF not found: {pdf_path}",
                stage="open",
            )

        logger.info(
            "opening_pdf",
            path=str(pdf_path),
            book_id=str(book_id),
        )

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as exc:
            raise IngestionError(
                f"Failed to open PDF: {exc}",
                stage="open",
            ) from exc

        total_pages = len(doc)
        book_dir = self._scratch / str(book_id)
        book_dir.mkdir(parents=True, exist_ok=True)

        results: list[tuple[ExtractedPage, Path]] = []

        for idx in range(total_pages):
            page_no = idx + 1
            try:
                page_path, page_doc = self._write_page(doc, idx, book_dir, page_no)
                extracted = self._build_model(
                    doc=doc,
                    idx=idx,
                    page_no=page_no,
                    total_pages=total_pages,
                    book_id=book_id,
                    chapter_id=chapter_id,
                )
                results.append((extracted, page_path))
            except IngestionError:
                raise
            except Exception as exc:
                raise IngestionError(
                    f"Failed on page {page_no}: {exc}",
                    stage="extract",
                    page_no=page_no,
                ) from exc

        doc.close()

        logger.info(
            "extraction_complete",
            book_id=str(book_id),
            total_pages=total_pages,
        )
        return results

    def get_pdf_info(self, pdf_path: str | Path) -> dict:
        """Return basic metadata about a PDF without extracting pages."""
        doc = fitz.open(str(pdf_path))
        info = {
            "page_count": len(doc),
            "metadata": dict(doc.metadata),
            "is_encrypted": doc.is_encrypted,
        }
        doc.close()
        return info

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _write_page(
        self,
        doc: fitz.Document,
        idx: int,
        book_dir: Path,
        page_no: int,
    ) -> tuple[Path, None]:
        output_path = book_dir / f"page_{page_no:03d}.pdf"
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=idx, to_page=idx)
        new_doc.save(str(output_path))
        new_doc.close()
        return output_path, None

    def _build_model(
        self,
        doc: fitz.Document,
        idx: int,
        page_no: int,
        total_pages: int,
        book_id: PyObjectId,
        chapter_id: PyObjectId | None,
    ) -> ExtractedPage:
        page = doc[idx]
        rect = page.rect
        text = page.get_text()
        has_images = len(page.get_images()) > 0
        word_count = len(text.split()) if text.strip() else 0

        return ExtractedPage(
            book_id=book_id,
            chapter_id=chapter_id,
            page_number=page_no,
            total_pages=total_pages,
            text_content=text or None,
            word_count=word_count,
            has_images=has_images,
            page_width=rect.width,
            page_height=rect.height,
            object_key=None,  # filled after MinIO upload
        )
