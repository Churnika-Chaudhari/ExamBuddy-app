"""Parse uploaded syllabus PDFs into subjects / units / topics and match PYQ topics."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from app.utils.subject_detector import normalize_subject_name
from app.utils.subject_matcher import subject_key
from app.utils.topic_extractor import _clean_topic_phrase, _title_case_topic, filter_topics, is_valid_topic

_SUBJECT_HEADER = re.compile(
    r"^(?:subject|paper|course)\s*(?:name|title|code)?\s*[:\-–—]\s*(.+)$",
    re.I,
)
_UNIT_HEADER = re.compile(
    r"^(?:unit|module|chapter|section|part)\s*[:=\-–—]?\s*"
    r"([IVXivx0-9]+|[A-Za-z])?\s*[:.\-–—)]?\s*(.*)$",
    re.I,
)
_ROMAN_MAP = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10,
}
_TOPIC_BULLET = re.compile(r"^[\-\*\u2022\u25cf\u25e6]\s+(.+)$")
_TOPIC_NUMBERED = re.compile(r"^(?:\d+[.)\]:]|\([a-z0-9]+\)|[a-z][.)])\s+(.+)$", re.I)
_ALL_CAPS_SUBJECT = re.compile(r"^[A-Z][A-Z0-9 &\-/]{2,60}$")
_NOISE_LINE = re.compile(
    r"^(syllabus|scheme|credit|hours?|marks?|semester|year|total|"
    r"teaching\s+scheme|examination\s+scheme|course\s+outcomes?|co\d+)\b",
    re.I,
)


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", (line or "").strip())


def _is_noise(line: str) -> bool:
    if not line or len(line) < 2:
        return True
    if _NOISE_LINE.match(line):
        return True
    if re.fullmatch(r"[\d\s.:\-–—/]+", line):
        return True
    return False


def _looks_like_subject_title(line: str) -> bool:
    if _SUBJECT_HEADER.match(line):
        return True
    if _ALL_CAPS_SUBJECT.match(line) and not _UNIT_HEADER.match(line):
        words = line.split()
        return 1 <= len(words) <= 6
    return False


def _parse_unit_number(raw: str | None) -> int | None:
    if not raw:
        return None
    token = str(raw).strip().lower()
    if token.isdigit():
        return int(token)
    return _ROMAN_MAP.get(token)


def extract_syllabus_structure(
    text: str,
    *,
    default_subject: str | None = None,
) -> dict[str, Any]:
    """
    Heuristic parse of syllabus text into subjects → units → topics/subtopics.

    Supports both single-subject and multi-subject syllabus documents.
    """
    raw_lines = [_normalize_line(ln) for ln in (text or "").splitlines()]
    lines = [ln for ln in raw_lines if ln and not _is_noise(ln)]

    subjects: list[dict[str, Any]] = []
    current_subject: dict[str, Any] | None = None
    current_unit: dict[str, Any] | None = None
    awaiting_module_title = False
    fallback_subject = normalize_subject_name(default_subject or "") or "General"

    def _ensure_subject(name: str) -> dict[str, Any]:
        nonlocal current_subject, current_unit, awaiting_module_title
        key = normalize_subject_name(name) or fallback_subject
        # "DBMS" (from the upload form) and "Database Management System" (from
        # the document header) are one subject, not two.
        match_key = subject_key(key)
        for existing in subjects:
            if existing["name"].lower() == key.lower() or (
                match_key and subject_key(existing["name"]) == match_key
            ):
                current_subject = existing
                current_unit = None
                awaiting_module_title = False
                return existing
        subject = {"name": key, "units": [], "topics": [], "subtopics": []}
        subjects.append(subject)
        current_subject = subject
        current_unit = None
        awaiting_module_title = False
        return subject

    def _ensure_unit(
        name: str,
        *,
        module_number: int | None = None,
        module_name: str | None = None,
    ) -> dict[str, Any]:
        nonlocal current_unit, awaiting_module_title
        subject = current_subject or _ensure_subject(fallback_subject)
        unit_name = _normalize_line(name) or "General Topics"
        for existing in subject["units"]:
            if existing["name"].lower() == unit_name.lower():
                current_unit = existing
                awaiting_module_title = not bool(existing.get("module_name"))
                return existing
        unit = {
            "name": unit_name,
            "module_number": module_number,
            "module_name": module_name or None,
            "topics": [],
            "subtopics": [],
        }
        subject["units"].append(unit)
        current_unit = unit
        awaiting_module_title = not bool(module_name)
        return unit

    def _add_topic(topic: str, *, is_subtopic: bool = False) -> None:
        nonlocal awaiting_module_title
        cleaned = _clean_topic_phrase(topic)
        if not cleaned or not is_valid_topic(cleaned):
            return
        display = _title_case_topic(cleaned)
        subject = current_subject or _ensure_subject(fallback_subject)
        unit = current_unit
        if unit is None:
            unit = _ensure_unit("General Topics", module_number=1, module_name="General Topics")
            awaiting_module_title = False

        # First plain title line after "MODULE II" becomes the module name.
        if awaiting_module_title and not is_subtopic and len(display.split()) <= 8:
            unit["module_name"] = display
            num = unit.get("module_number")
            unit["name"] = f"Module {num}: {display}" if num else display
            awaiting_module_title = False
            return

        bucket = unit["subtopics"] if is_subtopic else unit["topics"]
        subject_bucket = subject["subtopics"] if is_subtopic else subject["topics"]
        if display.lower() not in {t.lower() for t in bucket}:
            bucket.append(display)
        if display.lower() not in {t.lower() for t in subject_bucket}:
            subject_bucket.append(display)

    if default_subject:
        _ensure_subject(default_subject)

    for line in lines:
        subject_match = _SUBJECT_HEADER.match(line)
        if subject_match:
            _ensure_subject(subject_match.group(1))
            continue

        unit_match = _UNIT_HEADER.match(line)
        if unit_match:
            num_raw = (unit_match.group(1) or "").strip()
            rest = (unit_match.group(2) or "").strip()
            number = _parse_unit_number(num_raw)
            kind = "Module"
            lower = line.lower()
            if lower.startswith("unit"):
                kind = "Unit"
            elif lower.startswith("chapter"):
                kind = "Chapter"
            elif lower.startswith("section"):
                kind = "Section"
            elif lower.startswith("part"):
                kind = "Part"
            if number is not None and rest:
                label = f"{kind} {number}: {rest}"
                _ensure_unit(label, module_number=number, module_name=rest)
            elif number is not None:
                label = f"{kind} {number}"
                _ensure_unit(label, module_number=number, module_name=None)
            elif rest:
                _ensure_unit(rest, module_number=None, module_name=rest)
            else:
                _ensure_unit(kind, module_number=None, module_name=None)
            continue

        # Avoid treating module titles / short headers as new subjects when a unit is open.
        if (
            current_unit is None
            and _looks_like_subject_title(line)
            and len(line) <= 60
        ):
            _ensure_subject(line.title() if line.isupper() else line)
            continue

        bullet = _TOPIC_BULLET.match(line)
        if bullet:
            awaiting_module_title = False
            _add_topic(bullet.group(1))
            continue

        numbered = _TOPIC_NUMBERED.match(line)
        if numbered:
            awaiting_module_title = False
            if re.match(r"^\([a-z0-9]+\)", line, re.I) and current_unit:
                _add_topic(numbered.group(1), is_subtopic=True)
            else:
                _add_topic(numbered.group(1))
            continue

        # Plain topic-like lines under a unit (or pending module title).
        if current_unit and (awaiting_module_title or (is_valid_topic(line) and len(line.split()) <= 10)):
            _add_topic(line)

    if not subjects:
        _ensure_subject(fallback_subject)

    # Flat catalog for matching.
    catalog: list[dict[str, Any]] = []
    seen: set[str] = set()
    for subject in subjects:
        for unit in subject.get("units") or []:
            number = unit.get("module_number")
            module_name = unit.get("module_name") or unit.get("name") or "General Topics"
            for topic in (unit.get("topics") or []) + (unit.get("subtopics") or []):
                key = f"{subject['name']}|{topic}".lower()
                if key in seen:
                    continue
                seen.add(key)
                catalog.append(
                    {
                        "subject": subject["name"],
                        "unit": unit["name"],
                        "module_number": number,
                        "module_name": module_name,
                        "topic": topic,
                    }
                )
        for topic in subject.get("topics") or []:
            key = f"{subject['name']}|{topic}".lower()
            if key in seen:
                continue
            seen.add(key)
            catalog.append(
                {
                    "subject": subject["name"],
                    "unit": "General Topics",
                    "module_number": 1,
                    "module_name": "General Topics",
                    "topic": topic,
                }
            )

    return {
        "subjects": subjects,
        "catalog": catalog,
        "topic_names": [row["topic"] for row in catalog],
        "subject_names": [s["name"] for s in subjects if s.get("name")],
    }


def _similarity(a: str, b: str) -> float:
    a_n = a.lower().strip()
    b_n = b.lower().strip()
    if not a_n or not b_n:
        return 0.0
    if a_n == b_n:
        return 1.0
    if a_n in b_n or b_n in a_n:
        return 0.92
    return SequenceMatcher(None, a_n, b_n).ratio()


def match_topics_to_syllabus(
    analysis: dict[str, Any],
    syllabus_structure: dict[str, Any] | None,
    *,
    preferred_subject: str | None = None,
) -> dict[str, Any]:
    """
    Remap extracted PYQ topics onto syllabus canonical names / units when possible.
    Leaves topics unchanged when no good syllabus match exists.
    """
    if not analysis:
        return analysis
    catalog = list((syllabus_structure or {}).get("catalog") or [])
    if preferred_subject:
        pref = normalize_subject_name(preferred_subject).lower()
        preferred_rows = [r for r in catalog if str(r.get("subject", "")).lower() == pref]
        # Prefer subject-specific rows but keep others as fallback.
        catalog = preferred_rows + [r for r in catalog if r not in preferred_rows]

    if not catalog:
        return analysis

    def _best_match(topic: str) -> dict[str, str] | None:
        best: dict[str, str] | None = None
        best_score = 0.0
        for row in catalog:
            score = _similarity(topic, str(row.get("topic", "")))
            if score > best_score:
                best_score = score
                best = row
        if best and best_score >= 0.82:
            return best
        return None

    def _remap_row(row: dict[str, Any]) -> dict[str, Any] | None:
        raw = str(row.get("topic", "")).strip()
        cleaned = _clean_topic_phrase(raw) or raw
        topic = _title_case_topic(cleaned) if cleaned else ""
        if not topic or not is_valid_topic(topic):
            return None
        match = _best_match(topic)
        if not match:
            return {
                **row,
                "topic": topic,
                "unit": row.get("unit") or "General",
            }
        return {
            **row,
            "topic": match["topic"],
            "unit": match.get("unit") or row.get("unit") or "General",
            "syllabus_subject": match.get("subject"),
            "syllabus_matched": True,
        }

    # Remap frequency table / topic table.
    freq_table = []
    seen_topics: set[str] = set()
    for row in analysis.get("topic_frequency_table") or analysis.get("topic_table") or []:
        if not isinstance(row, dict):
            continue
        remapped = _remap_row(row)
        if not remapped:
            continue
        key = remapped["topic"].lower()
        if key in seen_topics:
            # Merge frequencies for duplicates after canonicalization.
            for existing in freq_table:
                if existing["topic"].lower() == key:
                    existing["frequency"] = int(existing.get("frequency") or 0) + int(
                        remapped.get("frequency") or 0
                    )
                    break
            continue
        seen_topics.add(key)
        freq_table.append(remapped)

    freq_table.sort(key=lambda r: int(r.get("frequency") or 0), reverse=True)

    topic_frequency = {r["topic"]: int(r.get("frequency") or 0) for r in freq_table}
    topic_table = [
        {
            "topic": r["topic"],
            "frequency": int(r.get("frequency") or 0),
            "importance": "High"
            if int(r.get("frequency") or 0) >= 3
            else ("Medium" if int(r.get("frequency") or 0) == 2 else "Low"),
        }
        for r in freq_table
    ]

    # Group by syllabus unit.
    groups: dict[str, list[str]] = {}
    for row in freq_table:
        unit = str(row.get("unit") or "General")
        groups.setdefault(unit, [])
        if row["topic"] not in groups[unit]:
            groups[unit].append(row["topic"])

    analysis = dict(analysis)
    analysis["topic_frequency_table"] = freq_table
    analysis["topic_table"] = topic_table
    analysis["topic_frequency"] = topic_frequency
    analysis["syllabus_topics"] = filter_topics([r["topic"] for r in freq_table])
    analysis["academic_topic_table"] = [
        {"topic": r["topic"], "frequency": int(r.get("frequency") or 0)} for r in freq_table
    ]
    analysis["topic_groups"] = [{"group": g, "topics": topics} for g, topics in groups.items()]
    analysis["important_topics"] = [
        {
            "topic": r["topic"],
            "score": round(int(r.get("frequency") or 1) / max(int(freq_table[0].get("frequency") or 1), 1), 2),
            "reason": "Matched to syllabus" if r.get("syllabus_matched") else "Extracted from PYQ",
        }
        for r in freq_table[:12]
    ]
    analysis["high_priority_topics"] = [r for r in freq_table if int(r.get("frequency") or 0) >= 3]
    analysis["medium_priority_topics"] = [r for r in freq_table if int(r.get("frequency") or 0) == 2]
    analysis["low_priority_topics"] = [r for r in freq_table if int(r.get("frequency") or 0) == 1]
    analysis["most_important_topics"] = analysis["high_priority_topics"]
    analysis["frequently_asked_topics"] = (
        analysis["high_priority_topics"] + analysis["medium_priority_topics"]
    )
    analysis["rarely_asked_topics"] = analysis["low_priority_topics"]
    analysis["syllabus_matched"] = True
    return analysis


def collect_syllabus_catalog(
    syllabus_docs: list[dict[str, Any]],
    *,
    preferred_subject: str | None = None,
) -> dict[str, Any]:
    """Merge syllabus_structure from multiple uploaded syllabus documents."""
    merged_catalog: list[dict[str, str]] = []
    subjects: list[dict[str, Any]] = []
    seen_topics: set[str] = set()
    seen_subjects: set[str] = set()
    pref = subject_key(preferred_subject)

    for doc in syllabus_docs:
        structure = doc.get("syllabus_structure") or {}
        if not structure and doc.get("extracted_text"):
            structure = extract_syllabus_structure(
                doc.get("extracted_text") or "",
                default_subject=doc.get("subject") or preferred_subject,
            )
        for subject in structure.get("subjects") or []:
            name = normalize_subject_name(subject.get("name") or "")
            if pref and subject_key(name) != pref:
                continue
            if name and name.lower() not in seen_subjects:
                seen_subjects.add(name.lower())
                subjects.append(subject)
        for row in structure.get("catalog") or []:
            topic = str(row.get("topic") or "").strip()
            if not topic:
                continue
            row_subject = subject_key(str(row.get("subject") or ""))
            if pref and row_subject and row_subject != pref:
                continue
            key = f"{row.get('subject','')}|{topic}".lower()
            if key in seen_topics:
                continue
            seen_topics.add(key)
            merged_catalog.append(
                {
                    "subject": str(row.get("subject") or "General"),
                    "unit": str(row.get("unit") or "General"),
                    "topic": topic,
                }
            )

    return {
        "subjects": subjects,
        "catalog": merged_catalog,
        "topic_names": [r["topic"] for r in merged_catalog],
        "subject_names": [s.get("name") for s in subjects if s.get("name")],
    }
