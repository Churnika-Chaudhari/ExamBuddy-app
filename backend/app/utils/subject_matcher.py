"""Canonical subject identity for matching a PYQ upload to a saved syllabus.

Matching is alias-driven, never fuzzy: two subject names are the same subject
only when they normalize to the same key or one of them is a curated alias of
the other (DBMS ↔ Database Management System). A near-miss string similarity
would silently attach the wrong syllabus to a PYQ, which is much worse than
falling back to "no syllabus found".
"""

from __future__ import annotations

import re

from app.utils.subject_detector import normalize_subject_name

# alias (already normalized) -> canonical subject key
_ALIASES: dict[str, str] = {}

# canonical key -> display name used when we have to name the subject ourselves
_CANONICAL_DISPLAY: dict[str, str] = {}

# Each entry: (display name, [aliases]). The display name is itself an alias.
_SUBJECT_ALIAS_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Database Management System",
        (
            "dbms",
            "rdbms",
            "database management system",
            "database management systems",
            "database system",
            "database systems",
            "database management",
            "relational database management system",
        ),
    ),
    (
        "Operating System",
        ("os", "operating system", "operating systems", "operating system concepts"),
    ),
    (
        "Computer Networks",
        (
            "cn",
            "computer network",
            "computer networks",
            "computer networking",
            "data communication and networking",
            "data communication and computer networks",
        ),
    ),
    (
        "Data Structures",
        (
            "ds",
            "dsa",
            "data structure",
            "data structures",
            "data structures and algorithms",
            "data structure and algorithm",
        ),
    ),
    (
        "Design and Analysis of Algorithms",
        ("daa", "design and analysis of algorithms", "analysis of algorithms", "algorithms"),
    ),
    (
        "Artificial Intelligence",
        ("ai", "artificial intelligence"),
    ),
    (
        "Machine Learning",
        ("ml", "machine learning"),
    ),
    (
        "Software Engineering",
        ("se", "software engineering", "software engineering and project management"),
    ),
    (
        "Theory of Computation",
        ("toc", "theory of computation", "automata theory", "formal languages and automata theory"),
    ),
    (
        "Computer Organization and Architecture",
        (
            "coa",
            "cao",
            "computer organization",
            "computer architecture",
            "computer organization and architecture",
        ),
    ),
    (
        "Object Oriented Programming",
        ("oop", "oops", "object oriented programming", "object oriented programming with c++"),
    ),
    (
        "Compiler Design",
        ("cd", "compiler design", "compiler construction", "principles of compiler design"),
    ),
    (
        "Cloud Computing",
        ("cc", "cloud computing"),
    ),
    (
        "Cyber Security",
        ("cyber security", "information security", "network security"),
    ),
    (
        "Web Technology",
        ("wt", "web technology", "web technologies", "web engineering"),
    ),
    (
        "Data Mining",
        ("dm", "data mining", "data mining and warehousing", "data warehousing and mining"),
    ),
    (
        "Software Testing",
        ("st", "software testing", "software testing and quality assurance"),
    ),
    (
        "Discrete Mathematics",
        ("discrete mathematics", "discrete structures", "discrete mathematical structures"),
    ),
    (
        "Microprocessor",
        ("mp", "microprocessor", "microprocessors", "microprocessor and microcontroller"),
    ),
    (
        "Java Programming",
        ("java", "java programming", "core java", "advanced java"),
    ),
    (
        "Python Programming",
        ("python", "python programming"),
    ),
)

_PUNCT = re.compile(r"[^a-z0-9]+")
_FILLER = re.compile(r"\b(?:and|the|of|with|for|in|to|a|an)\b")


def _normalize_key(name: str | None) -> str:
    """Lowercase, drop punctuation and filler words, collapse whitespace."""
    text = normalize_subject_name(name or "").lower()
    if not text:
        return ""
    text = _PUNCT.sub(" ", text)
    text = _FILLER.sub(" ", text)
    return " ".join(text.split())


def _build_alias_tables() -> None:
    for display, aliases in _SUBJECT_ALIAS_GROUPS:
        canonical = _normalize_key(display)
        _CANONICAL_DISPLAY[canonical] = display
        for alias in (display, *aliases):
            key = _normalize_key(alias)
            if key:
                _ALIASES[key] = canonical


_build_alias_tables()


def subject_key(name: str | None) -> str:
    """Stable identity key for a subject name — the syllabus upsert key.

    'DBMS', 'dbms', 'Database Management System' and 'Database Management
    Systems' all collapse to the same key; anything not in the curated alias
    table simply keeps its own normalized form.
    """
    key = _normalize_key(name)
    if not key:
        return ""
    return _ALIASES.get(key, key)


def canonical_subject_name(name: str | None) -> str:
    """Display name for a subject: the curated one when known, else as typed."""
    normalized = normalize_subject_name(name or "")
    key = subject_key(normalized)
    return _CANONICAL_DISPLAY.get(key) or normalized


def subjects_match(left: str | None, right: str | None) -> bool:
    """True only for an exact-or-alias match — deliberately not fuzzy."""
    left_key = subject_key(left)
    right_key = subject_key(right)
    return bool(left_key) and left_key == right_key


def subject_aliases(name: str | None) -> list[str]:
    """Every known spelling of a subject, for DB queries that need $in."""
    key = subject_key(name)
    if not key:
        return []
    aliases = {alias for alias, canonical in _ALIASES.items() if canonical == key}
    aliases.add(key)
    return sorted(aliases)


__all__ = [
    "canonical_subject_name",
    "subject_aliases",
    "subject_key",
    "subjects_match",
]
