"""
services/image_extraction_service.py

PyMuPDF-only image text extraction with TOC-based chapter tagging.

Extraction strategy:
  fitz.open() accepts image files directly (PNG, JPEG, TIFF, BMP, etc.).
  Each image is treated as a single-page document; text is extracted via a
  block-level pipeline that also handles tables and figure captions.

TOC detection:
  Images from scanned books have a Table of Contents page whose headings are
  rendered in a noticeably larger font than body text. The service detects this
  by comparing the maximum span font size on each image against the median max
  font size across all images in the batch. Any image whose max font size
  exceeds the median by a configurable factor (default 1.4×) is treated as the
  TOC image.

  TOC entries are expected in the form:
      <chapter name> ... <page number>
      e.g.  "Photosynthesis ... 12"

  The extracted entries are used to tag every ImageExtractionResult with
  `chapter_name` by mapping image_no → TOC page ranges.

Tables:
  PyMuPDF's page.find_tables() is applied where available; results are
  rendered as Markdown tables.

Figures / captions:
  Text blocks adjacent to embedded image sub-blocks are tagged with a
  [FIGURE CAPTION] prefix.

Batch interface:
  extract_batch(paths: list[Path]) -> list[ImageExtractionResult]
  Errors on individual images are isolated via ImageExtractionResult.error.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

from db.models.ocr import ExtractionMethod


SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp", ".pnm", ".pgm"}
)


_MIN_CHAR_COUNT = 50
_MIN_ALPHA_RATIO = 0.30
_MAX_SYMBOL_RATIO = 0.25


# An image is considered the TOC page if its largest font size is at least
# this many times greater than the median largest-font-size across all images.
_TOC_FONT_RATIO = 1.4

# Regex: "Some Chapter Name ... 42" or "Some Chapter Name 42"
# Captures (chapter_name, page_number). The dots/spaces between are optional.
_TOC_ENTRY_RE = re.compile(
    r"^(?P<chapter>.+?)\s*(?:\.{2,}|-{2,}|_{2,})?\s*(?P<page>\d+)\s*$"
)


@dataclass
class TocEntry:
    chapter_name: str
    page_no: int  # page number as printed in the TOC


@dataclass
class ImageExtractionResult:
    image_path: Path
    image_no: int  # 1-indexed position within the batch
    text: str
    extraction_method: ExtractionMethod
    char_count: int
    quality_score: float  # 0.0 – 1.0
    chapter_name: str | None = None  # resolved from TOC; None if no TOC found
    is_toc_image: bool = False  # True for the detected TOC image itself
    metadata: dict = field(default_factory=dict)
    error: str | None = None


def _table_to_markdown(table) -> str:
    rows = table.extract()
    if not rows:
        return ""
    rows = [[cell or "" for cell in row] for row in rows]
    header = rows[0]
    sep = ["---"] * len(header)
    body = rows[1:]
    lines = [
        "| " + " | ".join(str(c).strip().replace("\n", " ") for c in header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in body:
        lines.append(
            "| " + " | ".join(str(c).strip().replace("\n", " ") for c in row) + " |"
        )
    return "\n".join(lines)


def _quality_score(text: str) -> float:
    if not text or not text.strip():
        return 0.0
    total = len(text)
    alpha = sum(
        c.isalnum() or c in " \n\t.,;:!?-–—()[]{}'\"/\\%$@#&*+=<>" for c in text
    )
    replacement = text.count("\ufffd") + text.count("\x00")
    alpha_ratio = alpha / total if total else 0.0
    symbol_ratio = replacement / total if total else 0.0
    if total < _MIN_CHAR_COUNT:
        return 0.3 * (total / _MIN_CHAR_COUNT)
    return max(0.0, min(1.0, alpha_ratio - symbol_ratio * 2))


def _extract_image_page(page: fitz.Page) -> tuple[str, dict, float]:
    """
    Extract text from a fitz.Page opened from an image file.

    Returns (text, metadata, max_font_size).
    max_font_size is the largest span font size seen on the page; used by the
    TOC detector to identify heading-heavy pages.
    """
    metadata: dict = {}
    max_font_size: float = 0.0

    # --- Tables first ---
    table_texts: list[str] = []
    table_bboxes: list[fitz.Rect] = []
    try:
        tables = page.find_tables()
        for tbl in tables:
            md = _table_to_markdown(tbl)
            if md:
                table_texts.append(md)
                table_bboxes.append(tbl.bbox)
        if table_texts:
            metadata["tables_found"] = len(table_texts)
    except Exception:
        pass

    raw_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    blocks = raw_dict.get("blocks", [])

    image_bboxes: list[fitz.Rect] = [
        fitz.Rect(b["bbox"]) for b in blocks if b.get("type") == 1
    ]
    table_bbox_rects = [fitz.Rect(bb) for bb in table_bboxes]
    text_segments: list[str] = []

    for block in blocks:
        if block.get("type") != 0:
            continue

        block_rect = fitz.Rect(block["bbox"])

        if any(block_rect.intersects(tr) for tr in table_bbox_rects):
            continue

        near_image = any(
            abs(block_rect.y0 - ir.y1) < 40 or abs(ir.y0 - block_rect.y1) < 40
            for ir in image_bboxes
        )

        block_text = ""
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                span_size = span.get("size", 0.0)
                if span_size > max_font_size:
                    max_font_size = span_size
                block_text += span.get("text", "")
            block_text += "\n"

        block_text = block_text.strip()
        if not block_text:
            continue

        if near_image:
            block_text = f"[FIGURE CAPTION] {block_text}"
            metadata.setdefault("figure_captions", 0)
            metadata["figure_captions"] += 1

        text_segments.append(block_text)

    full_text = "\n\n".join(text_segments)
    if table_texts:
        full_text = full_text + "\n\n" + "\n\n".join(table_texts)

    return full_text, metadata, max_font_size


def _parse_toc_entries(text: str) -> list[TocEntry]:
    """
    Parse TOC entries from the extracted text of a TOC image.

    Expected line format:  <chapter name> [dots/dashes] <page number>
    e.g.  "Photosynthesis ... 12"  or  "Cell Division 34"

    Lines that don't match (blank lines, headers like "Contents") are skipped.
    """
    entries: list[TocEntry] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = _TOC_ENTRY_RE.match(line)
        if not m:
            continue
        chapter = m.group("chapter").strip(" .")
        page_no = int(m.group("page"))
        if chapter:
            entries.append(TocEntry(chapter_name=chapter, page_no=page_no))
    return entries


def _build_chapter_map(
    toc_entries: list[TocEntry],
    total_images: int,
) -> dict[int, str]:
    """
    Build a mapping of  image_no → chapter_name  using TOC page ranges.

    TOC page numbers are *book* page numbers (as printed). We treat image_no
    as a proxy for book page number (1-indexed, same order). Each chapter owns
    images from its start page up to (but not including) the next chapter's
    start page.

    Returns:
        dict mapping image_no (1-indexed) → chapter_name string.
        Images before the first TOC entry get chapter_name = None.
    """
    if not toc_entries:
        return {}

    # Sort by printed page number ascending
    sorted_entries = sorted(toc_entries, key=lambda e: e.page_no)

    chapter_map: dict[int, str] = {}
    for i, entry in enumerate(sorted_entries):
        start = entry.page_no
        end = (
            sorted_entries[i + 1].page_no
            if i + 1 < len(sorted_entries)
            else total_images + 1
        )
        for img_no in range(start, end):
            if 1 <= img_no <= total_images:
                chapter_map[img_no] = entry.chapter_name

    return chapter_map


def _detect_toc_index(
    max_font_sizes: list[float], ratio: float = _TOC_FONT_RATIO
) -> int | None:
    """
    Given the per-image max font sizes, return the 0-based index of the TOC
    image, or None if no image stands out clearly enough.

    Detection logic:
      - Compute the median max_font_size across all images.
      - The TOC image is the one whose max_font_size >= median * ratio AND
        is the largest overall (in case multiple heading-heavy pages exist).
    """
    if not max_font_sizes:
        return None

    valid = [s for s in max_font_sizes if s > 0]
    if not valid:
        return None

    median_size = statistics.median(valid)
    threshold = median_size * ratio

    candidates = [
        (size, idx) for idx, size in enumerate(max_font_sizes) if size >= threshold
    ]
    if not candidates:
        return None

    # Pick the image with the single largest heading font
    _, toc_idx = max(candidates, key=lambda x: x[0])
    return toc_idx


class ImageExtractionService:
    """
    PyMuPDF-only image text extraction service with TOC-based chapter tagging.

    Pass a batch of image paths (one image = one book page). The service:
      1. Extracts text from every image.
      2. Detects the TOC image by heading font-size heuristic.
      3. Parses TOC entries (chapter name + page number).
      4. Tags every ImageExtractionResult.chapter_name by mapping image_no
         against the TOC page ranges.

    Usage:
        service = ImageExtractionService()
        results = service.extract_batch(paths)
        for r in results:
            if r.error:
                logger.warning("Failed %s: %s", r.image_path, r.error)
                continue
            store(r.text, chapter=r.chapter_name, page=r.image_no)

    TOC tuning:
        Adjust `toc_font_ratio` in the constructor if detection is too
        aggressive (false positives) or too conservative (misses the TOC).
    """

    def __init__(
        self,
        *,
        min_char_count: int = _MIN_CHAR_COUNT,
        toc_font_ratio: float = _TOC_FONT_RATIO,
    ) -> None:
        self._min_char_count = min_char_count
        self._toc_font_ratio = toc_font_ratio

    def extract_batch(self, paths: list[Path]) -> list[ImageExtractionResult]:
        """
        Extract text from a batch of image files and tag each result with its
        chapter name derived from the TOC.

        Args:
            paths: Ordered list of image file paths (one per book page).
                   Supported formats: PNG, JPEG, TIFF, BMP, GIF, WebP, PNM, PGM.

        Returns:
            List of ImageExtractionResult in the same order as `paths`.
            Each result carries:
              - text            extracted text
              - chapter_name    resolved from TOC (None if TOC not found)
              - is_toc_image    True for the detected TOC page
              - quality_score   0.0 – 1.0
              - error           non-None if this image failed
        """
        if not paths:
            return []

        # Pass 1: extract every image, collect max font sizes for TOC detection
        raw_results: list[tuple[ImageExtractionResult, float]] = []
        for idx, path in enumerate(paths):
            result, max_font_size = self._extract_single(path, image_no=idx + 1)
            raw_results.append((result, max_font_size))

        # Pass 2: detect TOC image
        max_font_sizes = [fs for _, fs in raw_results]
        toc_idx = _detect_toc_index(max_font_sizes, ratio=self._toc_font_ratio)

        toc_entries: list[TocEntry] = []
        if toc_idx is not None:
            toc_result, _ = raw_results[toc_idx]
            toc_result.is_toc_image = True
            toc_entries = _parse_toc_entries(toc_result.text)
            toc_result.metadata["toc_entries_parsed"] = len(toc_entries)

        # Pass 3: build chapter map and tag results
        chapter_map = _build_chapter_map(toc_entries, total_images=len(paths))
        results: list[ImageExtractionResult] = []
        for result, _ in raw_results:
            result.chapter_name = chapter_map.get(result.image_no)
            results.append(result)

        return results

    def _extract_single(
        self, path: Path, image_no: int
    ) -> tuple[ImageExtractionResult, float]:
        """
        Extract one image. Returns (ImageExtractionResult, max_font_size).
        Never raises — errors surface in result.error; max_font_size is 0.0.
        """
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return (
                ImageExtractionResult(
                    image_path=path,
                    image_no=image_no,
                    text="",
                    extraction_method=ExtractionMethod.PYMUPDF,
                    char_count=0,
                    quality_score=0.0,
                    error=f"Unsupported file extension: {path.suffix!r}",
                ),
                0.0,
            )

        doc: fitz.Document = None
        try:
            doc = fitz.open(str(path))
            page = doc[0]
            text, meta, max_font_size = _extract_image_page(page)
            quality = _quality_score(text)

            return (
                ImageExtractionResult(
                    image_path=path,
                    image_no=image_no,
                    text=text,
                    extraction_method=ExtractionMethod.PYMUPDF,
                    char_count=len(text),
                    quality_score=round(quality, 4),
                    metadata=meta,
                ),
                max_font_size,
            )

        except Exception as exc:  # noqa: BLE001
            return (
                ImageExtractionResult(
                    image_path=path,
                    image_no=image_no,
                    text="",
                    extraction_method=ExtractionMethod.PYMUPDF,
                    char_count=0,
                    quality_score=0.0,
                    error=str(exc),
                ),
                0.0,
            )

        finally:
            if doc is not None:
                doc.close()
