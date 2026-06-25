"""
NCERT PDF Page Splitter (standalone utility)
=============================================

Renders each PDF page to a PNG image and writes a ``metadata.json``
alongside them. No MinIO or MongoDB required.

Output layout:
    <OUTPUT_DIR>/<book_name>/page_001.png
    <OUTPUT_DIR>/<book_name>/page_002.png
    ...
    <OUTPUT_DIR>/<book_name>/metadata.json

Usage:
    python scripts/split_pdfs.py

Environment variables:
    INPUT_DIR   - Source PDF directory  (default: ./data/input)
    OUTPUT_DIR  - Output root directory (default: ./data/output)
    RENDER_DPI  - Render resolution in DPI (default: 150)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import fitz  # PyMuPDF

# Allow running from the project root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

INPUT_DIR = Path(os.getenv("INPUT_DIR", "./data/input"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./data/output"))
RENDER_DPI = int(os.getenv("RENDER_DPI", "150"))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── helpers ────────────────────────────────────────────────────────────────


def _istnow() -> str:
    return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()


def _book_name(pdf_path: Path) -> str:
    return pdf_path.stem.lower().replace(" ", "_").replace("-", "_")


# ── core ───────────────────────────────────────────────────────────────────


def split_pdf(pdf_path: Path) -> dict:
    """
    Render every page of *pdf_path* to a PNG and return a summary dict.

    Output path per page:
        <OUTPUT_DIR>/<book_name>/page_<NNN>.png

    The zoom matrix is built from RENDER_DPI so that:
        zoom = DPI / 72   (72 pt = 1 inch in PDF user-space)
    """
    book_name = _book_name(pdf_path)
    book_dir = OUTPUT_DIR / book_name
    book_dir.mkdir(parents=True, exist_ok=True)

    zoom = RENDER_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    print(f"  Opening : {pdf_path.name}  (DPI={RENDER_DPI}, zoom={zoom:.2f}x)")

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    metadata_list: list[dict] = []

    for idx in range(total_pages):
        page_no = idx + 1
        filename = f"page_{page_no:03d}.png"
        out_path = book_dir / filename

        page = doc[idx]
        rect = page.rect
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        pixmap.save(str(out_path))

        text = page.get_text()
        word_count = len(text.split()) if text.strip() else 0
        has_images = len(page.get_images()) > 0

        metadata_list.append(
            {
                "book_name": book_name,
                "page_number": page_no,
                "total_pages": total_pages,
                "file_name": filename,
                "file_path": str(out_path.resolve()),
                "width_px": pixmap.width,
                "height_px": pixmap.height,
                "page_width_pt": rect.width,
                "page_height_pt": rect.height,
                "dpi": RENDER_DPI,
                "word_count": word_count,
                "has_images": has_images,
                "processed_at": _istnow(),
            }
        )

        print(
            f"    [{page_no:03d}/{total_pages}]  {out_path}  "
            f"({pixmap.width}×{pixmap.height}px)"
        )

    doc.close()

    # write metadata alongside the images
    meta_path = book_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(metadata_list, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Metadata: {meta_path}\n")

    return {
        "book_name": book_name,
        "total_pages": total_pages,
        "extracted": total_pages,
        "output_dir": str(book_dir.resolve()),
    }


# ── entry point ────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 60)
    print("NCERT PDF → PNG Page Splitter")
    print("=" * 60)

    if not INPUT_DIR.exists():
        print(f"❌  INPUT_DIR does not exist: {INPUT_DIR}")
        sys.exit(1)

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"⚠️   No PDFs found in {INPUT_DIR}")
        print("     Place source PDFs there and re-run.")
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF(s) in {INPUT_DIR}\n")

    results: list[dict] = []
    for pdf_file in pdf_files:
        try:
            result = split_pdf(pdf_file)
            results.append(result)
            print(
                f"  ✅  {result['book_name']}: "
                f"{result['extracted']}/{result['total_pages']} pages  →  "
                f"{result['output_dir']}\n"
            )
        except Exception as exc:
            print(f"  ❌  {pdf_file.name}: {exc}\n")

    total_pages = sum(r["total_pages"] for r in results)
    total_extracted = sum(r["extracted"] for r in results)

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Books processed : {len(results)}")
    print(f"  Pages rendered  : {total_extracted}/{total_pages}")
    print(f"  Output location : {OUTPUT_DIR.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
