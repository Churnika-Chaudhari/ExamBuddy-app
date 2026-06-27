"""Infer academic subject from PYQ filename or document title."""

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
    ("Web Technology", [r"web\s*technology", r"web\s*engineering", r"html", r"javascript"]),
    ("Information Technology", [r"information\s*technology", r"\bit\b"]),
    ("Data Structures", [r"data\s*structure", r"\bds\b"]),
    ("Computer Organization", [r"computer\s*organization", r"computer\s*architecture"]),
    ("Cloud Computing", [r"cloud\s*computing"]),
    ("Cyber Security", [r"cyber\s*security", r"information\s*security", r"network\s*security"]),
]


def normalize_subject_name(name: str) -> str:
    return " ".join(name.strip().split())


def detect_subject_from_text(text: str) -> str | None:
    if not text or not text.strip():
        return None
    haystack = text.lower().replace("_", " ").replace("-", " ")
    for canonical, patterns in _SUBJECT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, haystack, re.IGNORECASE):
                return canonical
    return None


def resolve_document_subject(
    *,
    explicit_subject: str | None,
    filename: str | None,
    title: str | None,
) -> str | None:
    if explicit_subject and explicit_subject.strip():
        return normalize_subject_name(explicit_subject)
    for source in (filename, title):
        if not source:
            continue
        detected = detect_subject_from_text(source)
        if detected:
            return detected
    return None
