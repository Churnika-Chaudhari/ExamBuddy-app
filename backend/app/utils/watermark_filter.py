"""
Detect and remove PDF watermarks, headers, footers, and scanner boilerplate
before topic analysis.
"""

from __future__ import annotations

import re
from collections import Counter

# Explicit watermark / scanner / footer patterns
_WATERMARK_REGEXES = [
    re.compile(r"^\s*confidential\s*$", re.I),
    re.compile(r"^\s*draft\s*$", re.I),
    re.compile(r"^\s*sample\s*(copy)?\s*$", re.I),
    re.compile(r"^\s*do not (copy|distribute|print)\s*$", re.I),
    re.compile(r"^\s*for internal use only\s*$", re.I),
    re.compile(r"^\s*watermark\s*$", re.I),
    re.compile(r"^\s*scanned\s+(with|by)\s+", re.I),
    re.compile(r"camscanner", re.I),
    re.compile(r"genius\s*scan", re.I),
    re.compile(r"adobe\s*scan", re.I),
    re.compile(r"microsoft\s*lens", re.I),
    re.compile(r"^\s*page\s*\d+\s*(of\s*\d+)?\s*$", re.I),
    re.compile(r"^\s*-\s*\d+\s*-\s*$"),
    re.compile(r"^\s*\d+\s*/\s*\d+\s*$"),
    re.compile(r"https?://\S+", re.I),
    re.compile(r"www\.\S+", re.I),
    re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.I),
    re.compile(r"^\s*copyright\s+", re.I),
    re.compile(r"^\s*all rights reserved\s*$", re.I),
    re.compile(r"^\s*downloaded\s+from\s+", re.I),
    re.compile(r"^\s*printed\s+on\s+", re.I),
    re.compile(r"^\s*scanned\s+document\s*$", re.I),
    re.compile(r"^\s*preview\s+(only|copy)\s*$", re.I),
    re.compile(r"^\s*university\s+of\s+", re.I),
    re.compile(r"^\s*institute\s+of\s+(technology|engineering)\s*$", re.I),
    re.compile(r"^\s*examination\s+(branch|section|division)\s*$", re.I),
    re.compile(r"^\s*roll\s*no\.?\s*[:.]?\s*$", re.I),
    re.compile(r"^\s*seat\s*no\.?\s*[:.]?\s*$", re.I),
    re.compile(r"^\s*signature\s+of\s+", re.I),
    re.compile(r"^\s*invigilator", re.I),
]

# Lines that are only symbols / very short noise (common in watermark layers)
_NOISE_LINE = re.compile(r"^[\s\d\W_\-–—|/\\.:;,*#@!%^&+=<>]{1,20}$")

# Known watermark phrases (substring match on normalized line)
_KNOWN_PHRASES = (
    "scanned with",
    "scanned by",
    "cam scanner",
    "sample copy",
    "water mark",
    "watermark",
    "not for sale",
    "for personal use",
    "digitally signed",
    "electronically generated",
    "this is a computer generated",
    "photo copy",
    "photocopy",
    "duplicate copy",
    "trial version",
    "evaluation only",
)


def _normalize_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    return line.lower()


def _is_known_watermark_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if len(stripped) <= 2:
        return True
    if _NOISE_LINE.match(stripped):
        return True
    for pattern in _WATERMARK_REGEXES:
        if pattern.search(stripped):
            return True
    norm = _normalize_line(stripped)
    if any(phrase in norm for phrase in _KNOWN_PHRASES):
        return True
    return False


def _lines_from_page_text(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


def _detect_cross_page_repeats(
    pages: list[list[str]],
    *,
    min_page_ratio: float = 0.35,
    max_line_length: int = 150,
) -> set[str]:
    """Lines repeated across many pages → headers, footers, watermarks."""
    num_pages = len(pages)
    if num_pages < 2:
        return set()

    line_page_hits: Counter[str] = Counter()
    for page_lines in pages:
        seen_on_page: set[str] = set()
        for line in page_lines:
            norm = _normalize_line(line)
            if not norm or len(norm) > max_line_length:
                continue
            if norm not in seen_on_page:
                seen_on_page.add(norm)
                line_page_hits[norm] += 1

    threshold = max(2, int(num_pages * min_page_ratio))
    return {norm for norm, count in line_page_hits.items() if count >= threshold}


def _detect_position_repeats(pages: list[list[str]]) -> set[str]:
    """First/last lines repeated on most pages → headers and footers."""
    if len(pages) < 2:
        return set()

    top_counter: Counter[str] = Counter()
    bottom_counter: Counter[str] = Counter()

    for page_lines in pages:
        if not page_lines:
            continue
        for line in page_lines[:2]:
            norm = _normalize_line(line)
            if norm and len(norm) < 120:
                top_counter[norm] += 1
        for line in page_lines[-2:]:
            norm = _normalize_line(line)
            if norm and len(norm) < 120:
                bottom_counter[norm] += 1

    threshold = max(2, int(len(pages) * 0.5))
    repeated: set[str] = set()
    for counter in (top_counter, bottom_counter):
        for norm, count in counter.items():
            if count >= threshold:
                repeated.add(norm)
    return repeated


def filter_page_lines(
    lines: list[str],
    *,
    repeated_norms: set[str],
) -> list[str]:
    kept: list[str] = []
    for line in lines:
        norm = _normalize_line(line)
        if norm in repeated_norms:
            continue
        if _is_known_watermark_line(line):
            continue
        kept.append(line)
    return kept


def remove_watermarks_from_pages(page_texts: list[str]) -> str:
    """
    Remove watermark lines from per-page PDF text and return cleaned full text.
    """
    if not page_texts:
        return ""

    pages_as_lines = [_lines_from_page_text(t) for t in page_texts]
    cross_page = _detect_cross_page_repeats(pages_as_lines)
    position_repeats = _detect_position_repeats(pages_as_lines)
    repeated = cross_page | position_repeats

    cleaned_pages: list[str] = []
    for page_lines in pages_as_lines:
        filtered = filter_page_lines(page_lines, repeated_norms=repeated)
        if filtered:
            cleaned_pages.append("\n".join(filtered))

    text = "\n\n".join(cleaned_pages).strip()
    return _cleanup_residual_watermarks(text)


def remove_watermarks_from_text(text: str) -> str:
    """Filter watermarks from already-extracted plain text."""
    if not text.strip():
        return text

    pages = text.split("\n\n---\n\n") if "---" in text else [text]
    if len(pages) == 1:
        # Treat double-newline blocks as pseudo-pages for repeat detection
        blocks = [b for b in re.split(r"\n{3,}", text) if b.strip()]
        if len(blocks) >= 2:
            pages = blocks

    if len(pages) >= 2:
        return remove_watermarks_from_pages(pages)

    lines = _lines_from_page_text(text)
    filtered = filter_page_lines(lines, repeated_norms=set())
    return _cleanup_residual_watermarks("\n".join(filtered))


def _cleanup_residual_watermarks(text: str) -> str:
    """Final pass: drop empty lines and isolated watermark remnants."""
    out_lines: list[str] = []
    for line in text.splitlines():
        if _is_known_watermark_line(line):
            continue
        out_lines.append(line.rstrip())

    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(out_lines)).strip()
    return cleaned
