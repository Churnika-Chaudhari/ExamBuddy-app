import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.utils.text_sanitizer import clean_extracted_text
from app.utils.watermark_filter import remove_watermarks_from_pages, remove_watermarks_from_text

logger = logging.getLogger(__name__)

# Below this many characters a page is treated as scanned/empty and sent to OCR.
_MIN_CHARS_PER_PAGE = 40
# 160 DPI is ~2x faster than 220 with little quality loss for exam papers.
_OCR_DPI = 160
_OCR_WORKERS = 3
# Skip OCR entirely when embedded text is already plentiful.
_TEXT_RICH_CHARS_PER_PAGE = 450
_TEXT_RICH_SPARSE_RATIO = 0.2
# Cap image OCR width for speed.
_IMAGE_OCR_MAX_WIDTH = 1600

_ocr_checked = False
_ocr_ready = False


def _ocr_available() -> bool:
    """Return True only if pytesseract AND the tesseract binary are usable."""
    global _ocr_checked, _ocr_ready
    if _ocr_checked:
        return _ocr_ready
    _ocr_checked = True
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        _ocr_ready = True
    except Exception as exc:  # binary missing, import error, etc.
        logger.info("OCR not available (%s); scanned PDFs will rely on embedded text", exc)
        _ocr_ready = False
    return _ocr_ready


def _ocr_image(image: Any) -> str:
    import pytesseract

    return pytesseract.image_to_string(image).strip()


def _render_page_image(doc: Any, index: int):
    from PIL import Image

    page = doc[index]
    pix = page.get_pixmap(dpi=_OCR_DPI)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def _should_skip_ocr(page_texts: list[str], sparse_pages: list[int]) -> bool:
    """True when the PDF already has enough selectable text."""
    page_count = max(len(page_texts), 1)
    total_chars = sum(len((t or "").strip()) for t in page_texts)
    sparse_ratio = len(sparse_pages) / page_count
    return (
        total_chars >= _TEXT_RICH_CHARS_PER_PAGE * page_count
        and sparse_ratio <= _TEXT_RICH_SPARSE_RATIO
    )


def _ocr_sparse_pages(doc: Any, page_texts: list[str], sparse_pages: list[int]) -> int:
    """OCR sparse pages in parallel. Returns how many pages were replaced."""
    if not sparse_pages:
        return 0

    # Render sequentially (PyMuPDF doc is not thread-safe), OCR in parallel.
    rendered: list[tuple[int, Any]] = []
    for i in sparse_pages:
        try:
            rendered.append((i, _render_page_image(doc, i)))
        except Exception as exc:
            logger.warning("PDF render failed for page %d: %s", i + 1, exc)

    if not rendered:
        return 0

    replaced = 0
    workers = min(_OCR_WORKERS, len(rendered))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_ocr_image, image): idx for idx, image in rendered}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                ocr_text = fut.result() or ""
            except Exception as exc:
                logger.warning("PDF OCR failed for page %d: %s", idx + 1, exc)
                continue
            if len(ocr_text) > len(page_texts[idx].strip()):
                page_texts[idx] = ocr_text
                replaced += 1
    return replaced


def extract_text_from_pdf(file_bytes: bytes) -> tuple[str, int]:
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = doc.page_count

        # sort=True orders text blocks top→bottom, left→right so multi-column
        # question papers are read in the correct sequence.
        page_texts: list[str] = []
        sparse_pages: list[int] = []
        for i, page in enumerate(doc):
            text = page.get_text("text", sort=True)
            page_texts.append(text)
            if len(text.strip()) < _MIN_CHARS_PER_PAGE:
                sparse_pages.append(i)

        ocr_replaced = 0
        if sparse_pages and _ocr_available():
            if _should_skip_ocr(page_texts, sparse_pages):
                logger.info(
                    "Skipping OCR — text-rich PDF pages=%d sparse=%d",
                    page_count,
                    len(sparse_pages),
                )
            else:
                logger.info(
                    "Running parallel OCR on %d sparse PDF page(s) dpi=%d",
                    len(sparse_pages),
                    _OCR_DPI,
                )
                ocr_replaced = _ocr_sparse_pages(doc, page_texts, sparse_pages)

        doc.close()

        raw_text = "\n".join(page_texts).strip()
        cleaned = remove_watermarks_from_pages(page_texts)
        if not cleaned.strip():
            logger.warning("Watermark filter removed all text; using lightly filtered raw text")
            cleaned = remove_watermarks_from_text(raw_text)

        cleaned = clean_extracted_text(cleaned)
        logger.info(
            "PDF extraction done pages=%d chars=%d sparse=%d ocr_replaced=%d",
            page_count,
            len(cleaned),
            len(sparse_pages),
            ocr_replaced,
        )
        return cleaned, page_count
    except Exception as exc:
        logger.error("PDF extraction failed: %s", exc)
        raise


def extract_text_from_docx(file_bytes: bytes) -> tuple[str, int]:
    try:
        from docx import Document

        document = Document(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
        text = "\n".join(paragraphs).strip()
        return remove_watermarks_from_text(text), 1
    except Exception as exc:
        logger.error("DOCX extraction failed: %s", exc)
        raise


def extract_text_from_image(file_bytes: bytes) -> tuple[str, int]:
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(file_bytes))
        if image.width > _IMAGE_OCR_MAX_WIDTH:
            ratio = _IMAGE_OCR_MAX_WIDTH / float(image.width)
            image = image.resize(
                (_IMAGE_OCR_MAX_WIDTH, max(1, int(image.height * ratio))),
                Image.Resampling.BILINEAR,
            )
        text = _ocr_image(image)
        return remove_watermarks_from_text(text), 1
    except Exception as exc:
        logger.error("Image OCR failed: %s", exc)
        raise


def extract_text(file_bytes: bytes, file_type: str) -> dict[str, Any]:
    logger.info("Text extraction start file_type=%s bytes=%d", file_type, len(file_bytes or b""))
    if file_type == "pdf":
        text, page_count = extract_text_from_pdf(file_bytes)
    elif file_type == "docx":
        text, page_count = extract_text_from_docx(file_bytes)
        text = clean_extracted_text(text)
    elif file_type == "image":
        text, page_count = extract_text_from_image(file_bytes)
        text = clean_extracted_text(text)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    logger.info(
        "Text extraction complete file_type=%s pages=%d chars=%d preview=%r",
        file_type,
        page_count,
        len(text),
        (text[:120] + "…") if len(text) > 120 else text,
    )
    return {"text": text, "page_count": page_count}
