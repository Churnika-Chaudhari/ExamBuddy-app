"""Infer academic subject from PYQ filename, title, or paper text."""

from __future__ import annotations

import re

# (canonical name, keyword patterns)
_SUBJECT_PATTERNS: list[tuple[str, list[str]]] = [
    ("DBMS", [r"dbms", r"database\s*management", r"database\s*system", r"rdbms"]),
    ("Computer Networks", [r"computer\s*network", r"data\s*communication", r"\bcn\b", r"networking"]),
    ("Java Programming", [r"\bjava\b", r"java\s*programming"]),
    ("Python", [r"\bpython\b", r"python\s*programming"]),
    ("Operating System", [r"operating\s*system", r"\bos\b"]),
    ("Artificial Intelligence", [r"artificial\s*intelligence", r"\bai\b", r"machine\s*learning"]),
    ("Software Engineering", [r"software\s*engineering", r"software\s*design"]),
    ("Web Technology", [r"web\s*technology", r"web\s*engineering"]),
    ("Data Mining", [r"data\s*mining"]),
    ("Wireless Technology", [r"wireless\s*technology"]),
    ("Software Architecture", [r"software\s*architecture"]),
    ("AIDS", [r"\baids\b", r"ai\s*&\s*ds", r"artificial\s*intelligence\s*and\s*data"]),
    ("Information Technology", [r"information\s*technology"]),
    ("Data Structures", [r"data\s*structure", r"\bds\b"]),
    ("Computer Organization", [r"computer\s*organization", r"computer\s*architecture"]),
    ("Cloud Computing", [r"cloud\s*computing"]),
    ("Cyber Security", [r"cyber\s*security", r"information\s*security", r"network\s*security"]),
]

_GENERIC_TITLE = re.compile(
    r"^(pyq|notes|syllabus)\s*set\b|"
    r"^(question\s*paper|previous\s*year|model\s*paper|sample\s*paper)\b|"
    r"^untitled\b",
    re.I,
)

_FILENAME_NOISE = re.compile(
    r"\b("
    r"pyq|previous\s*year(?:\s*question)?s?|question\s*papers?|model\s*papers?|"
    r"sample\s*papers?|end\s*sem(?:ester)?|mid\s*sem(?:ester)?|semester|"
    r"sem\s*\d+|univ(?:ersity)?|exam|papers?|set\s*\d+|batch\s*\d+|"
    r"may|june|nov|dec|jan|feb|mar|apr|jul|aug|sep|oct|"
    r"pdf|docx?"
    r")\b",
    re.I,
)

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_SUBJECT_HEADER = re.compile(
    r"(?:^|\n)\s*(?:subject|course|paper)\s*(?:name|title|code)?\s*[:\-–—]\s*([^\n|]+)",
    re.I,
)


def normalize_subject_name(name: str) -> str:
    return " ".join((name or "").strip().split())


def detect_subject_from_text(text: str) -> str | None:
    if not text or not text.strip():
        return None
    haystack = text.lower().replace("_", " ").replace("-", " ")
    for canonical, patterns in _SUBJECT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, haystack, re.IGNORECASE):
                return canonical
    return None


def subject_from_label(raw: str | None) -> str | None:
    """Derive a usable subject label from a filename or document title."""
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip()
    text = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", text)
    text = text.replace("_", " ").replace("-", " ")
    if _GENERIC_TITLE.match(text):
        return None
    text = _FILENAME_NOISE.sub(" ", text)
    text = _YEAR.sub(" ", text)
    text = re.sub(r"[^\w\s&/+]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ._-")
    if not text or len(text) < 2:
        return None
    if re.fullmatch(r"\d+", text):
        return None
    if _GENERIC_TITLE.match(text):
        return None
    # Keep short ALL-CAPS / mixed tokens (WebX, AIDS) as-is; title-case longer names.
    if text.isupper() or (len(text) <= 12 and " " not in text):
        return normalize_subject_name(text)
    return normalize_subject_name(text.title() if text.islower() else text)


def extract_subject_from_paper_text(text: str | None) -> str | None:
    """Pull subject from common question-paper headers like 'Subject: WebX'."""
    if not text:
        return None
    sample = text[:4000]
    match = _SUBJECT_HEADER.search(sample)
    if match:
        candidate = subject_from_label(match.group(1))
        if candidate:
            return candidate
    return detect_subject_from_text(sample)


def resolve_document_subject(
    *,
    explicit_subject: str | None,
    filename: str | None = None,
    title: str | None = None,
    extracted_text: str | None = None,
) -> str | None:
    if explicit_subject and explicit_subject.strip():
        return normalize_subject_name(explicit_subject)

    # Prefer cleaned filename/title labels (keeps names like WebX / AIDS)
    # before keyword remapping to longer canonical course names.
    for source in (filename, title):
        derived = subject_from_label(source)
        if derived:
            return derived

    for source in (filename, title):
        if not source:
            continue
        detected = detect_subject_from_text(source)
        if detected:
            return detected

    if extracted_text:
        from_paper = extract_subject_from_paper_text(extracted_text)
        if from_paper:
            return from_paper

    return None
