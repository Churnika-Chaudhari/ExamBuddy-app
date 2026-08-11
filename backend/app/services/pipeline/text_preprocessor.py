"""
PYQ text cleaning before topic extraction and Gemini prompts.

Pipeline: raw extract → watermark removal → exam noise removal →
question pattern cleanup → deduplication → normalized text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.utils.watermark_filter import remove_watermarks_from_text

# Exam boilerplate — drop only when the line is purely administrative.
_PURE_INSTRUCTION_LINE = re.compile(
    r"^\s*(?:"
    r"attempt\s+(?:any|all|the following)\s+questions?|"
    r"answer\s+(?:all|any)\s+questions?|"
    r"choose\s+(?:one|any)\s*$|"
    r"instructions?\s*(?:to|:|\-)?\s*$|"
    r"note\s*:\s*$|"
    r"time\s*:\s*\d|"
    r"maximum\s+marks?|"
    r"total\s+marks?\s*$|"
    r"marks?\s*:\s*\d+\s*$|"
    r"duration\s*:|"
    r"semester\s+examination|"
    r"end\s+semester|"
    r"mid\s+semester|"
    r"question\s+paper|"
    r"course\s+code|"
    r"subject\s+code|"
    r"roll\s+no|"
    r"seat\s+no|"
    r"date\s*:\s*\d"
    r")\s*$",
    re.I,
)

_QUESTION_PREFIX = re.compile(
    r"^(?:"
    r"(?:Q(?:uestion)?\.?\s*)?\d+[\).\]:\-]|"
    r"\([a-z]\)|"
    r"[ivxIVX]+[\).\]:]|"
    r"CO[\-\s]?\d+|"
    r"Unit[\-\s]?\d+|"
    r"U[\-\s]?\d+"
    r")\s*",
    re.I,
)

_MARKS_SUFFIX = re.compile(
    r"(?:"
    r"\[\s*\d+\s*(?:marks?|m)\s*\]|"
    r"\(\s*\d+\s*(?:marks?|m)\s*\)|"
    r"\b\d+\s*(?:marks?|m)\b"
    r")\s*$",
    re.I,
)

_CO_TAG = re.compile(r"\bCO[\-\s]?\d+\b", re.I)
_UNIT_TAG = re.compile(r"\b(?:Unit|U)[\-\s]?\d+\b", re.I)
_PAGE_NUM = re.compile(r"^\s*(?:page|pg\.?)\s*\d+\s*$", re.I)
_ROMAN_ONLY = re.compile(r"^\s*[ivxIVX]+[\).\]]?\s*$")

_BULLET_ONLY = re.compile(r"^\s*[\u2022\u2023\u2043\u2219\-\*•]\s*$")

# Standalone "OR" between questions
_OR_LINE = re.compile(r"^\s*(?:OR|or)\s*$")

# Repeated whitespace / broken OCR
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_MULTI_NEWLINE = re.compile(r"\n{3,}")

# Page number patterns embedded in lines
_INLINE_PAGE = re.compile(r"\b(?:page|pg\.?)\s*\d+\b", re.I)


@dataclass
class PreprocessStats:
    original_chars: int
    cleaned_chars: int
    lines_removed: int
    lines_deduplicated: int


@dataclass
class PreprocessResult:
    cleaned_text: str
    question_lines: list[str]
    stats: PreprocessStats


def _normalize_line(line: str) -> str:
    line = line.replace("\u00a0", " ")
    line = _MULTI_SPACE.sub(" ", line.strip())
    return line


def _should_drop_line(line: str) -> bool:
    if not line or len(line) < 3:
        return True
    if _PAGE_NUM.match(line):
        return True
    if _ROMAN_ONLY.match(line):
        return True
    if _BULLET_ONLY.match(line):
        return True
    if _OR_LINE.match(line):
        return True
    if _PURE_INSTRUCTION_LINE.match(line):
        return True
    # Pure marks line e.g. "10 Marks"
    if re.match(r"^\d+\s*(?:marks?|m)\.?$", line, re.I):
        return True
    return False


def _clean_question_line(line: str) -> str:
    line = _QUESTION_PREFIX.sub("", line)
    line = _MARKS_SUFFIX.sub("", line)
    line = _CO_TAG.sub("", line)
    line = _UNIT_TAG.sub("", line)
    line = _INLINE_PAGE.sub("", line)
    line = re.sub(r"^\s*[\u2022\u2023\u2043\u2219\-\*•]\s+", "", line)
    return _normalize_line(line)


def _dedupe_lines(lines: list[str]) -> tuple[list[str], int]:
    seen: set[str] = set()
    out: list[str] = []
    removed = 0
    for line in lines:
        key = re.sub(r"\s+", " ", line.lower().strip())
        if not key or key in seen:
            removed += 1
            continue
        seen.add(key)
        out.append(line)
    return out, removed


def _is_question_candidate(line: str) -> bool:
    if len(line) < 12:
        return False
    if "?" in line:
        return True
    return bool(
        re.search(
            r"\b("
            r"explain|define|describe|write|discuss|what is|what are|list|state|"
            r"mention|differentiate|compare|illustrate|derive|prove|sketch|draw"
            r")\b",
            line,
            re.I,
        )
    )


def preprocess_pyq_text(raw_text: str) -> PreprocessResult:
    """Full cleaning pass on extracted PYQ text."""
    original_len = len(raw_text or "")
    text = remove_watermarks_from_text(raw_text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    raw_lines = text.splitlines()
    cleaned_lines: list[str] = []
    removed = 0

    for raw in raw_lines:
        line = _normalize_line(raw)
        if _should_drop_line(line):
            removed += 1
            continue
        line = _clean_question_line(line)
        if _should_drop_line(line) or len(line) < 8:
            removed += 1
            continue
        cleaned_lines.append(line)

    cleaned_lines, deduped = _dedupe_lines(cleaned_lines)

    question_lines = [ln for ln in cleaned_lines if _is_question_candidate(ln)]
    if not question_lines:
        # Fallback: paragraph chunks that look like questions
        chunks = re.split(r"\n{2,}|(?:\s+OR\s+)", text)
        for chunk in chunks:
            chunk = _clean_question_line(_normalize_line(chunk))
            if 15 <= len(chunk) <= 600 and _is_question_candidate(chunk):
                question_lines.append(chunk)

    question_lines = question_lines[:800]
    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = _MULTI_NEWLINE.sub("\n\n", cleaned_text).strip()

    stats = PreprocessStats(
        original_chars=original_len,
        cleaned_chars=len(cleaned_text),
        lines_removed=removed,
        lines_deduplicated=deduped,
    )
    return PreprocessResult(
        cleaned_text=cleaned_text,
        question_lines=question_lines,
        stats=stats,
    )
