#!/usr/bin/env python3
"""
NCERT PDF Ingestion Script
===========================

CLI entry point for ingesting a directory of NCERT PDFs into MongoDB + MinIO.

Usage:
    python scripts/ingest_pdfs.py

    # Override input directory:
    INPUT_DIR=./data/input python scripts/ingest_pdfs.py

    # Override class and subject (for a single-book run):
    PDF_CLASS_NO=8 PDF_SUBJECT=Science python scripts/ingest_pdfs.py

Environment Variables (in addition to .env):
    INPUT_DIR       - Directory containing source PDFs (default: ./data/input)
    PDF_CLASS_NO    - Default class number applied to all PDFs (default: 8)
    PDF_SUBJECT     - Default subject applied to all PDFs (default: "General")
    SKIP_EXISTING   - Skip already-uploaded pages, "true"/"false" (default: true)
    LOG_LEVEL       - Logging level passed to configure_logging (default: INFO)

Notes:
    Book metadata (class_no, subject, title, edition) is inferred from the PDF
    filename when not explicitly provided.  The file stem is used as the title;
    underscores/hyphens are replaced with spaces and capitalised.

    To associate pages with a chapter at ingestion time, pass chapter_id to
    IngestionService.ingest_book() directly from a custom script.
"""

import asyncio
import os
import sys
from pathlib import Path

# Allow running from the project root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.logging import configure_logging, get_logger
from services.ingestion.ingestion_service import IngestionService

logger = get_logger(__name__)


def _book_meta_from_path(pdf_path: Path, class_no: int, subject: str) -> dict:
    """Derive title from filename; caller supplies class_no and subject."""
    stem = pdf_path.stem
    title = stem.replace("_", " ").replace("-", " ").title()
    return {
        "title": title,
        "class_no": class_no,
        "subject": subject,
        "edition": None,
        "academic_year": None,
    }


async def run(
    input_dir: Path,
    class_no: int,
    subject: str,
    skip_existing: bool,
) -> list[dict]:
    service = IngestionService()
    pdf_files = sorted(input_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning("no_pdfs_found", input_dir=str(input_dir))
        return []

    logger.info("pipeline_started", pdf_count=len(pdf_files))

    results = []
    for pdf_file in pdf_files:
        meta = _book_meta_from_path(pdf_file, class_no, subject)
        try:
            summary = await service.ingest_book(
                pdf_path=pdf_file,
                skip_existing=skip_existing,
                **meta,
            )
            results.append(summary)
        except Exception as exc:
            logger.error(
                "book_ingestion_failed",
                file=pdf_file.name,
                error=str(exc),
            )
            results.append(
                {
                    "book_id": None,
                    "file": pdf_file.name,
                    "total_pages": 0,
                    "uploaded": 0,
                    "skipped": 0,
                    "failed": 0,
                    "error": str(exc),
                }
            )

    return results


def _print_summary(results: list[dict]) -> None:
    total_uploaded = sum(r.get("uploaded", 0) for r in results)
    total_skipped = sum(r.get("skipped", 0) for r in results)
    total_failed = sum(r.get("failed", 0) for r in results)
    total_pages = sum(r.get("total_pages", 0) for r in results)

    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"  Books processed : {len(results)}")
    print(f"  Total pages     : {total_pages}")
    print(f"  Uploaded        : {total_uploaded}")
    print(f"  Skipped         : {total_skipped}")
    print(f"  Failed          : {total_failed}")
    print("=" * 60)

    for r in results:
        status = "✅" if r.get("failed", 0) == 0 else "⚠️"
        book_label = r.get("book_id") or r.get("file", "unknown")
        print(
            f"  {status}  {book_label}: "
            f"{r.get('uploaded', 0)}/{r.get('total_pages', 0)} pages uploaded"
        )

    if total_failed > 0:
        print(f"\n⚠️  {total_failed} page(s) failed — check logs for details.")


def main() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO")
    configure_logging(log_level)

    input_dir = Path(os.getenv("INPUT_DIR", "./data/input"))
    class_no = int(os.getenv("PDF_CLASS_NO", "8"))
    subject = os.getenv("PDF_SUBJECT", "General")
    skip_existing = os.getenv("SKIP_EXISTING", "true").lower() != "false"

    if not input_dir.exists():
        print(f"❌ INPUT_DIR does not exist: {input_dir}")
        sys.exit(1)

    results = asyncio.run(
        run(
            input_dir=input_dir,
            class_no=class_no,
            subject=subject,
            skip_existing=skip_existing,
        )
    )

    _print_summary(results)

    total_failed = sum(r.get("failed", 0) for r in results)
    sys.exit(1 if total_failed > 0 else 0)


if __name__ == "__main__":
    main()
