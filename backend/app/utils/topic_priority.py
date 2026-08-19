"""Aggregate PYQ topic occurrences and classify exam priority per subject."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Literal

from app.repositories.generated_notes_repository import normalize_topic_key
from app.utils.topic_extractor import _title_case_topic, filter_topics, is_valid_topic

PriorityLevel = Literal["High", "Medium", "Low"]

_PUNCT = re.compile(r"[^\w\s/+&]")
_SPACE = re.compile(r"\s+")


def canonical_topic_key(name: str) -> str:
    """Stable key for deduplicating near-identical topic labels."""
    key = normalize_topic_key(name or "")
    key = _PUNCT.sub(" ", key)
    key = key.replace("-", " ")
    key = _SPACE.sub(" ", key).strip()
    return key


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        if len(shorter) >= 4 and shorter in longer:
            return 0.93
    return SequenceMatcher(None, a, b).ratio()


def resolve_canonical_name(
    topic: str,
    *,
    syllabus_names: list[str] | None = None,
) -> str:
    """Prefer syllabus name when a close match exists; otherwise title-case cleaned topic."""
    cleaned = _title_case_topic((topic or "").strip())
    if not cleaned:
        return ""
    key = canonical_topic_key(cleaned)
    best_name = cleaned
    best_score = 0.0
    for name in syllabus_names or []:
        score = _similarity(key, canonical_topic_key(name))
        if score > best_score:
            best_score = score
            best_name = name
    if best_score >= 0.82:
        return best_name
    return cleaned


def classify_priority(
    *,
    frequency: int,
    max_frequency: int,
    total_marks: float | None = None,
    max_marks: float | None = None,
    paper_count: int = 1,
    analyzed_papers: int = 1,
) -> tuple[PriorityLevel, float]:
    """
    Relative priority for a subject dataset.

    score = 0.7 * occurrence_ratio + 0.3 * marks_ratio (marks optional)
    Small datasets (< 3 papers) use softer thresholds so rare topics aren't all High.
    """
    freq = max(0, int(frequency or 0))
    max_f = max(1, int(max_frequency or 1))
    occurrence_score = min(100.0, (freq / max_f) * 100.0)

    marks_score = 0.0
    has_marks = total_marks is not None and max_marks is not None and float(max_marks) > 0
    if has_marks:
        marks_score = min(100.0, (float(total_marks or 0) / float(max_marks)) * 100.0)
        priority_score = 0.7 * occurrence_score + 0.3 * marks_score
    else:
        priority_score = occurrence_score

    papers = max(1, int(analyzed_papers or 1))

    # Soften classification when few papers exist.
    if papers <= 1:
        if freq >= 3 and priority_score >= 70:
            level: PriorityLevel = "High"
        elif freq >= 2 and priority_score >= 45:
            level = "Medium"
        else:
            level = "Low"
    elif papers == 2:
        if priority_score >= 85 and freq >= 3:
            level = "High"
        elif priority_score >= 55 and freq >= 2:
            level = "Medium"
        else:
            level = "Low"
    else:
        if priority_score >= 80:
            level = "High"
        elif priority_score >= 50:
            level = "Medium"
        else:
            level = "Low"

    # Single appearance across many papers stays Low/Medium unless score is high.
    if paper_count <= 1 and papers >= 3 and freq <= 1:
        level = "Low"
        priority_score = min(priority_score, 40.0)

    return level, round(priority_score, 1)


def _row_marks(row: dict[str, Any]) -> float | None:
    """Return marks only when explicitly present on the analysis row (never invent)."""
    for key in ("total_marks", "marks", "mark"):
        if key in row and row[key] is not None:
            try:
                value = float(row[key])
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
    return None


def aggregate_subject_topics(
    analyses: list[dict[str, Any]],
    *,
    extract_topics,
    syllabus_topic_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Merge topics across completed analyses for one subject.

    occurrence_count  = sum of per-paper question frequencies (not duplicate extractions)
    paper_count       = distinct analyses/papers where the topic appears
    total_marks       = sum of explicit marks when available, else omitted
    """
    # key -> aggregate
    buckets: dict[str, dict[str, Any]] = {}
    # For fuzzy merge of near-duplicates into an existing bucket key
    known_keys: list[str] = []

    syllabus_names = list(syllabus_topic_names or [])

    def _find_bucket_key(topic: str) -> str:
        key = canonical_topic_key(topic)
        if not key:
            return ""
        if key in buckets:
            return key
        for existing in known_keys:
            if _similarity(key, existing) >= 0.88:
                return existing
        return key

    for analysis in analyses:
        analysis_id = str(analysis.get("_id") or analysis.get("id") or "")
        paper_topics_seen: set[str] = set()  # avoid double-counting same topic rows in one paper

        for row in extract_topics(analysis):
            raw_topic = str(row.get("topic") or "").strip()
            if not raw_topic or not is_valid_topic(raw_topic):
                continue
            if not filter_topics([raw_topic]):
                continue

            display = resolve_canonical_name(raw_topic, syllabus_names=syllabus_names)
            # Prefer syllabus-matched name from the analysis row when present.
            if row.get("syllabus_matched") and row.get("topic"):
                display = resolve_canonical_name(str(row["topic"]), syllabus_names=syllabus_names)

            bkey = _find_bucket_key(display)
            if not bkey:
                continue

            freq = max(1, int(row.get("frequency") or 1))
            marks = _row_marks(row)

            if bkey not in buckets:
                buckets[bkey] = {
                    "topic": display,
                    "unit": row.get("unit") or "General",
                    "occurrence_count": 0,
                    "paper_count": 0,
                    "total_marks": 0.0,
                    "has_marks": False,
                    "analysis_ids": [],
                    "last_occurrence": analysis.get("completed_at") or analysis.get("created_at"),
                }
                known_keys.append(bkey)
            else:
                # Prefer longer / syllabus-looking display names.
                current = buckets[bkey]["topic"]
                if display.lower() in {n.lower() for n in syllabus_names}:
                    buckets[bkey]["topic"] = display
                elif len(display) > len(current) and _similarity(
                    canonical_topic_key(display), bkey
                ) >= 0.9:
                    buckets[bkey]["topic"] = display
                if row.get("unit") and (
                    not buckets[bkey].get("unit") or buckets[bkey]["unit"] == "General"
                ):
                    buckets[bkey]["unit"] = row.get("unit")

            # Within one paper, count question frequency once (max if duplicate rows).
            if bkey in paper_topics_seen:
                # Already counted this topic for this paper; take max extra freq only.
                continue
            paper_topics_seen.add(bkey)

            buckets[bkey]["occurrence_count"] += freq
            buckets[bkey]["paper_count"] += 1
            if analysis_id and analysis_id not in buckets[bkey]["analysis_ids"]:
                buckets[bkey]["analysis_ids"].append(analysis_id)

            stamp = analysis.get("completed_at") or analysis.get("created_at")
            if stamp and (
                not buckets[bkey].get("last_occurrence")
                or stamp > buckets[bkey]["last_occurrence"]
            ):
                buckets[bkey]["last_occurrence"] = stamp

            if marks is not None:
                buckets[bkey]["total_marks"] += marks
                buckets[bkey]["has_marks"] = True

    if not buckets:
        return []

    analyzed_papers = len(analyses)
    max_freq = max(int(b["occurrence_count"]) for b in buckets.values()) or 1
    max_marks = max(
        (float(b["total_marks"]) for b in buckets.values() if b.get("has_marks")),
        default=0.0,
    )

    results: list[dict[str, Any]] = []
    for data in buckets.values():
        occ = int(data["occurrence_count"])
        papers = int(data["paper_count"])
        total_marks = float(data["total_marks"]) if data.get("has_marks") else None
        level, score = classify_priority(
            frequency=occ,
            max_frequency=max_freq,
            total_marks=total_marks,
            max_marks=max_marks if max_marks > 0 else None,
            paper_count=papers,
            analyzed_papers=analyzed_papers,
        )
        item: dict[str, Any] = {
            "topic": data["topic"],
            "unit": data.get("unit") or "General",
            "frequency": occ,  # backward compatible alias for occurrence
            "occurrence_count": occ,
            "paper_count": papers,
            "importance": level,
            "priority": level,
            "priority_score": score,
            "analysis_ids": data.get("analysis_ids") or [],
            "last_occurrence": data.get("last_occurrence"),
        }
        if total_marks is not None:
            item["total_marks"] = round(total_marks, 1)
        results.append(item)

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    results.sort(
        key=lambda r: (
            priority_rank.get(str(r.get("priority") or "Low"), 9),
            -int(r.get("occurrence_count") or 0),
            str(r.get("topic") or "").lower(),
        )
    )
    return results


def exam_priority_label(
    priority: str | None,
    *,
    occurrence_count: int | None = None,
    paper_count: int | None = None,
    total_marks: float | None = None,
    module: str | None = None,
    subject: str | None = None,
) -> str:
    """Human-readable priority context string for AI note generation."""
    level = (priority or "").strip().title() or "Standard"
    parts: list[str] = []
    if subject:
        parts.append(f"Subject: {subject}")
    if module:
        parts.append(f"Module: {module}")
    parts.append(f"Priority: {level}")
    if occurrence_count:
        parts.append(f"Asked {occurrence_count} time{'s' if occurrence_count != 1 else ''}")
    if paper_count:
        parts.append(
            f"Appeared in {paper_count} paper{'s' if paper_count != 1 else ''}"
        )
    if total_marks is not None and total_marks > 0:
        parts.append(f"Total marks: {total_marks:g}")
    if level == "High":
        parts.append("Write comprehensive exam-oriented notes for this syllabus module topic.")
    elif level == "Medium":
        parts.append("Write sufficient exam coverage notes for this syllabus module topic.")
    elif level == "Low":
        parts.append(
            "Write concise but complete notes for this syllabus topic. Do not omit important concepts."
        )
    return " | ".join(parts)
