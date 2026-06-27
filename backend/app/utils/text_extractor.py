import io
import logging
from typing import Any

from app.utils.watermark_filter import remove_watermarks_from_pages, remove_watermarks_from_text

logger = logging.getLogger(__name__)

# Below this many characters a page is treated as scanned/empty and sent to OCR.
_MIN_CHARS_PER_PAGE = 40
_OCR_DPI = 220

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


def _ocr_pdf_page(doc: Any, index: int) -> str:
    try:
        import pytesseract
        from PIL import Image

        page = doc[index]
        pix = page.get_pixmap(dpi=_OCR_DPI)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return pytesseract.image_to_string(image).strip()
    except Exception as exc:
        logger.warning("PDF OCR failed for page %d: %s", index + 1, exc)
        return ""


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

        # OCR fallback: scanned/image-only pages produce little or no text.
        if sparse_pages and _ocr_available():
            logger.info("Running OCR on %d sparse PDF page(s)", len(sparse_pages))
            for i in sparse_pages:
                ocr_text = _ocr_pdf_page(doc, i)
                if len(ocr_text) > len(page_texts[i].strip()):
                    page_texts[i] = ocr_text

        doc.close()

        raw_text = "\n".join(page_texts).strip()
        cleaned = remove_watermarks_from_pages(page_texts)
        if not cleaned.strip():
            logger.warning("Watermark filter removed all text; using lightly filtered raw text")
            cleaned = remove_watermarks_from_text(raw_text)

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
        import pytesseract

        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image).strip()
        return remove_watermarks_from_text(text), 1
    except Exception as exc:
        logger.error("Image OCR failed: %s", exc)
        raise


def extract_text(file_bytes: bytes, file_type: str) -> dict[str, Any]:
    if file_type == "pdf":
        text, page_count = extract_text_from_pdf(file_bytes)
    elif file_type == "docx":
        text, page_count = extract_text_from_docx(file_bytes)
    elif file_type == "image":
        text, page_count = extract_text_from_image(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    return {"text": text, "page_count": page_count}
