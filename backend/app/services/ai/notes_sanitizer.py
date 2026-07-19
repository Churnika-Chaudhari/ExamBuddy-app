"""Strip internal metadata and document noise from generated study notes."""

from __future__ import annotations

import re

# Lines that are system/RAG scaffolding — drop entirely.
_DROP_LINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*\[Source\s+\d+:", re.I),
    re.compile(r"^\s*>\s*FROM\s+UPLOADED", re.I),
    re.compile(r"^\s*FROM\s+UPLOADED\s+DOCUMENTS", re.I),
    re.compile(r"^\s*RETRIEVED\s+CONTENT", re.I),
    re.compile(r"^\s*={3,}.+={3,}\s*$"),
    re.compile(r"^\s*Configure\s+OPENAI_API_KEY", re.I),
    re.compile(r"^\s*Add\s+OPENAI_API_KEY", re.I),
    re.compile(r"^\s*_Based on retrieved content", re.I),
    re.compile(r"^\s*Generated from your uploaded", re.I),
    re.compile(r"^\s*\[?\s*Source\s*\d*\s*:\s*.+\.(pdf|docx?)\s*\]?\s*$", re.I),
    re.compile(r"^\s*(CO|Course\s+Outcome)\s*[\d\-–]+", re.I),
    re.compile(r"^\s*MAX\.?\s*MARKS", re.I),
    re.compile(r"^\s*TIME\s*:\s*\d", re.I),
    re.compile(r"^\s*Q\d+\.", re.I),
    re.compile(r"^\s*\[\d+\s*Marks?\]", re.I),
)

# Inline patterns to remove from otherwise valid lines.
_INLINE_STRIP = re.compile(
    r"\[Source\s+\d+:\s*[^\]]+\]|"
    r"FROM UPLOADED DOCUMENTS|"
    r"RETRIEVED CONTENT FROM UPLOADED DOCUMENTS|"
    r">\s*FROM UPLOADED DOCUMENTS?",
    re.I,
)

# Standalone subject/university codes (e.g. 51423) on their own or in headers.
_SUBJECT_CODE_LINE = re.compile(r"^\s*(Subject\s*(Code|No\.?)?\s*:?\s*)?\d{4,6}\s*$", re.I)
_SUBJECT_CODE_PREFIX = re.compile(r"^(Subject\s*(Code|No\.?)?\s*:?\s*)\d{4,6}\s*[-–—]\s*", re.I)

# Credit-system / syllabus boilerplate.
_BOILERPLATE_LINE = re.compile(
    r"^\s*(Credit\s+System|Choice\s+Based|CBCS|Semester|Scheme\s+of\s+Examination)\b",
    re.I,
)

# Motivational / meta filler that must never reach students.
_FILLER_LINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"this topic is important", re.I),
    re.compile(r"this is (a )?high[- ]priority topic", re.I),
    re.compile(r"frequently asked in exams?", re.I),
    re.compile(r"often asked in exams?", re.I),
    re.compile(r"you should study", re.I),
    re.compile(r"students? (should|must|need to) (study|revise|remember|learn)", re.I),
    re.compile(r"revise this carefully", re.I),
    re.compile(r"make sure to (study|revise)", re.I),
    re.compile(r"⭐\s*frequently asked", re.I),
    re.compile(r"^\s*exam priority\b", re.I),
)


def sanitize_note_text(text: str) -> str:
    """Remove metadata, filenames, filler, and exam-paper scaffolding from note text."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []

    for raw in text.split("\n"):
        line = _INLINE_STRIP.sub("", raw).strip()
        if not line:
            continue

        if any(p.search(line) for p in _DROP_LINE_PATTERNS):
            continue
        if any(p.search(line) for p in _FILLER_LINE_PATTERNS):
            continue
        if _SUBJECT_CODE_LINE.match(line):
            continue
        if _BOILERPLATE_LINE.match(line):
            continue

        line = _SUBJECT_CODE_PREFIX.sub("", line).strip()
        if not line:
            continue

        # Drop lines that are mostly a PDF filename.
        if re.search(r"\.pdf\b", line, re.I) and len(line) < 120:
            if re.search(r"[/\\]|Source\s+\d|uploaded", line, re.I):
                continue

        out.append(line)

    cleaned = "\n".join(out)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def sanitize_rag_passage(text: str) -> str:
    """Clean a single passage before sending to the AI (not shown to students)."""
    if not text:
        return ""
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if any(p.search(line) for p in _DROP_LINE_PATTERNS):
            continue
        if _SUBJECT_CODE_LINE.match(line):
            continue
        if _BOILERPLATE_LINE.match(line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()
