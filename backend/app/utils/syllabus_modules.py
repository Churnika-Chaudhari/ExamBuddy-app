"""Build Subject → Module → Topic trees from syllabus structure + PYQ occurrence."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.utils.subject_matcher import subject_key
from app.utils.topic_priority import (
    _similarity,
    canonical_topic_key,
    classify_priority,
)

_ROMAN = {
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
    "xi": 11,
    "xii": 12,
}

_UNIT_PREFIX = re.compile(
    r"^(?:unit|module|chapter|section|part)\s*"
    r"([IVXivx0-9]+)?\s*[:.\-–—)]*\s*(.*)$",
    re.I,
)

# Confident match → assign to syllabus topic. Below this → Other / Unmapped.
_MATCH_THRESHOLD = 0.82


def make_topic_id(topic_name: str) -> str:
    key = canonical_topic_key(topic_name) or "unknown"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return f"t_{digest}"


def make_module_id(module_number: int | None, module_name: str) -> str:
    key = f"{module_number or 0}|{canonical_topic_key(module_name)}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"m_{digest}"


def parse_module_number(raw: str | None) -> int | None:
    if not raw:
        return None
    token = str(raw).strip().lower()
    if token.isdigit():
        return int(token)
    if token in _ROMAN:
        return _ROMAN[token]
    return None


def split_unit_label(unit_label: str) -> tuple[int | None, str]:
    """
    Split 'Module 2: Testing Techniques' / 'Unit I Introduction' into
    (module_number, module_name).
    """
    label = (unit_label or "").strip()
    if not label:
        return None, "General Topics"
    match = _UNIT_PREFIX.match(label)
    if match:
        number = parse_module_number(match.group(1))
        rest = (match.group(2) or "").strip(" :-–—")
        if rest:
            return number, rest
        if number is not None:
            return number, f"Module {number}"
        return None, label
    return None, label


def _empty_occurrence() -> dict[str, Any]:
    return {
        "occurrence_count": 0,
        "paper_count": 0,
        "frequency": 0,
        "total_marks": None,
        "priority": "Low",
        "priority_score": 0.0,
        "importance": "Low",
        "analysis_ids": [],
        "last_occurrence": None,
        "asked": False,
    }


def _apply_occurrence(base: dict[str, Any], occ: dict[str, Any] | None) -> dict[str, Any]:
    if not occ:
        return {**base, **_empty_occurrence()}
    out = {**base}
    out["occurrence_count"] = int(occ.get("occurrence_count") or occ.get("frequency") or 0)
    out["paper_count"] = int(occ.get("paper_count") or 0)
    out["frequency"] = out["occurrence_count"]
    out["priority"] = occ.get("priority") or occ.get("importance") or "Low"
    out["importance"] = out["priority"]
    out["priority_score"] = float(occ.get("priority_score") or 0)
    out["analysis_ids"] = list(occ.get("analysis_ids") or [])
    out["last_occurrence"] = occ.get("last_occurrence")
    out["asked"] = out["occurrence_count"] > 0
    if occ.get("total_marks") is not None:
        out["total_marks"] = occ.get("total_marks")
    else:
        out["total_marks"] = None
    return out


def match_pyq_topic_to_syllabus(
    pyq_topic: str,
    syllabus_topics: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, float, bool]:
    """
    Returns (matched_syllabus_topic, score, needs_review).
    Only returns a match when score >= MATCH_THRESHOLD.
    Near-misses (0.62–0.81) are not assigned (needs_review=True, match=None).
    """
    key = canonical_topic_key(pyq_topic)
    if not key or not syllabus_topics:
        return None, 0.0, False

    best: dict[str, Any] | None = None
    best_score = 0.0
    for row in syllabus_topics:
        score = _similarity(key, canonical_topic_key(str(row.get("topic_name") or "")))
        if score > best_score:
            best_score = score
            best = row

    if best and best_score >= _MATCH_THRESHOLD:
        return best, best_score, False
    if best and best_score >= 0.62:
        return None, best_score, True  # uncertain — do not force-assign
    return None, best_score, False


def extract_subject_modules_from_catalog(
    catalog: list[dict[str, Any]],
    *,
    preferred_subject: str | None = None,
) -> list[dict[str, Any]]:
    """
    Build ordered modules from a syllabus catalog (subject/unit/topic rows).
    """
    pref = subject_key(preferred_subject)
    rows = list(catalog or [])
    if pref:
        # Alias-aware, never fuzzy: a DBMS PYQ may only use the "Database
        # Management System" rows, but must never borrow another subject's.
        preferred = [r for r in rows if subject_key(str(r.get("subject") or "")) == pref]
        rows = preferred

    modules_map: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for row in rows:
        topic_name = str(row.get("topic") or "").strip()
        if not topic_name:
            continue
        unit_label = str(row.get("unit") or "General Topics")
        number, module_name = split_unit_label(unit_label)
        # Prefer explicit fields when present on richer structures.
        if row.get("module_number") is not None:
            try:
                number = int(row["module_number"])
            except (TypeError, ValueError):
                pass
        if row.get("module_name"):
            module_name = str(row["module_name"]).strip() or module_name

        mid = make_module_id(number, module_name)
        if mid not in modules_map:
            modules_map[mid] = {
                "module_id": mid,
                "module_number": number,
                "module_name": module_name,
                "display_name": (
                    f"Module {number} — {module_name}" if number is not None else module_name
                ),
                "topics": [],
                "_topic_keys": set(),
            }
            order.append(mid)

        tkey = canonical_topic_key(topic_name)
        if tkey in modules_map[mid]["_topic_keys"]:
            continue
        modules_map[mid]["_topic_keys"].add(tkey)
        modules_map[mid]["topics"].append(
            {
                "topic_id": make_topic_id(topic_name),
                "topic_name": topic_name,
                "topic": topic_name,
                "unit": modules_map[mid]["display_name"],
                "module_id": mid,
                "module_number": number,
                "module_name": module_name,
                "from_syllabus": True,
            }
        )

    modules: list[dict[str, Any]] = []
    for mid in order:
        mod = modules_map[mid]
        mod.pop("_topic_keys", None)
        modules.append(mod)
    return modules


def modules_from_saved_syllabus(
    saved_modules: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Expand a stored syllabus module list into the runtime module shape.

    The `syllabi` collection stores modules compactly — module_number,
    module_name and a list of topic names. PYQ mapping, filtering and the
    mobile UI all consume the richer shape produced by the extraction
    helpers below, so both paths converge here rather than growing a second
    module pipeline.
    """
    modules: list[dict[str, Any]] = []
    for idx, saved in enumerate(saved_modules or [], start=1):
        if not isinstance(saved, dict):
            continue
        module_name = str(saved.get("module_name") or "").strip() or f"Module {idx}"
        number = saved.get("module_number")
        try:
            number = int(number) if number is not None else None
        except (TypeError, ValueError):
            number = None
        mid = str(saved.get("module_id") or "") or make_module_id(number, module_name)
        display_name = str(saved.get("display_name") or "").strip() or (
            f"Module {number} — {module_name}" if number is not None else module_name
        )

        topics: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in saved.get("topics") or []:
            name = str(raw.get("topic_name") or raw.get("topic") or "") if isinstance(raw, dict) else str(raw)
            name = name.strip()
            if not name:
                continue
            tkey = canonical_topic_key(name)
            if tkey in seen:
                continue
            seen.add(tkey)
            topics.append(
                {
                    "topic_id": make_topic_id(name),
                    "topic_name": name,
                    "topic": name,
                    "unit": display_name,
                    "module_id": mid,
                    "module_number": number,
                    "module_name": module_name,
                    "from_syllabus": True,
                }
            )

        modules.append(
            {
                "module_id": mid,
                "module_number": number,
                "module_name": module_name,
                "display_name": display_name,
                "topics": topics,
            }
        )
    return modules


def compact_modules_for_storage(
    modules: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Reduce runtime modules to the persisted syllabus shape."""
    compact: list[dict[str, Any]] = []
    for mod in modules or []:
        if mod.get("is_unmapped") or mod.get("is_fallback"):
            continue
        compact.append(
            {
                "module_id": mod.get("module_id"),
                "module_number": mod.get("module_number"),
                "module_name": mod.get("module_name"),
                "display_name": mod.get("display_name"),
                "topics": [
                    str(t.get("topic_name") or t.get("topic") or "").strip()
                    for t in (mod.get("topics") or [])
                    if str(t.get("topic_name") or t.get("topic") or "").strip()
                ],
            }
        )
    return compact


def extract_subject_modules_from_structure(
    structure: dict[str, Any] | None,
    *,
    preferred_subject: str | None = None,
) -> list[dict[str, Any]]:
    """Prefer a saved syllabus, then rich subjects[].units, then the catalog."""
    if not structure:
        return []

    # A syllabus loaded from the `syllabi` collection already has its modules
    # resolved for this subject — no need to re-parse the document catalog.
    if structure.get("modules"):
        saved = modules_from_saved_syllabus(structure.get("modules"))
        if saved:
            return saved

    pref = subject_key(preferred_subject)
    subjects = list(structure.get("subjects") or [])
    chosen = None
    if pref:
        # Only an exact or alias match counts, and a subject entry without
        # units is useless — a combined syllabus often declares the short name
        # ("DBMS") separately from the section that carries the modules.
        for s in subjects:
            if subject_key(s.get("name") or "") == pref and (s.get("units") or []):
                chosen = s
                break
    if chosen is None and len(subjects) == 1:
        chosen = subjects[0]

    if chosen and (chosen.get("units") or []):
        modules: list[dict[str, Any]] = []
        for idx, unit in enumerate(chosen.get("units") or [], start=1):
            unit_label = str(unit.get("name") or f"Module {idx}")
            number = unit.get("module_number")
            module_name = unit.get("module_name")
            if number is None or not module_name:
                parsed_n, parsed_name = split_unit_label(unit_label)
                number = number if number is not None else parsed_n
                module_name = module_name or parsed_name
            if number is None:
                number = idx
            mid = make_module_id(int(number) if number is not None else idx, str(module_name))
            topic_names = list(unit.get("topics") or []) + list(unit.get("subtopics") or [])
            # If module name was mistakenly stored as first topic, keep it as module name only.
            topics = []
            seen: set[str] = set()
            for name in topic_names:
                name = str(name).strip()
                if not name:
                    continue
                if canonical_topic_key(name) == canonical_topic_key(str(module_name)):
                    continue
                tkey = canonical_topic_key(name)
                if tkey in seen:
                    continue
                seen.add(tkey)
                topics.append(
                    {
                        "topic_id": make_topic_id(name),
                        "topic_name": name,
                        "topic": name,
                        "unit": f"Module {number} — {module_name}",
                        "module_id": mid,
                        "module_number": number,
                        "module_name": module_name,
                        "from_syllabus": True,
                    }
                )
            modules.append(
                {
                    "module_id": mid,
                    "module_number": int(number) if number is not None else idx,
                    "module_name": str(module_name),
                    "display_name": f"Module {number} — {module_name}",
                    "topics": topics,
                }
            )
        if modules:
            return modules

    return extract_subject_modules_from_catalog(
        list(structure.get("catalog") or []),
        preferred_subject=preferred_subject,
    )


def build_module_topic_tree(
    *,
    syllabus_structure: dict[str, Any] | None,
    pyq_topics: list[dict[str, Any]],
    preferred_subject: str | None = None,
    analyzed_paper_count: int = 0,
) -> dict[str, Any]:
    """
    Merge syllabus modules (structure) with PYQ occurrence (importance).

    - Every syllabus topic appears even if never asked.
    - PYQ topics that cannot be confidently matched go under Other / Unmapped.
    """
    modules = extract_subject_modules_from_structure(
        syllabus_structure,
        preferred_subject=preferred_subject,
    )
    has_syllabus_modules = bool(modules)

    # Flat syllabus topic index for matching.
    syllabus_topics: list[dict[str, Any]] = []
    for mod in modules:
        for t in mod.get("topics") or []:
            syllabus_topics.append(t)

    # Index PYQ aggregates by canonical key for quick attach after match.
    pyq_by_key: dict[str, dict[str, Any]] = {}
    for row in pyq_topics or []:
        name = str(row.get("topic") or "").strip()
        if not name:
            continue
        pyq_by_key[canonical_topic_key(name)] = row

    matched_pyq_keys: set[str] = set()
    needs_review: list[dict[str, Any]] = []

    # Attach occurrence onto syllabus topics.
    for mod in modules:
        enriched = []
        for t in mod.get("topics") or []:
            best_key = None
            best_row = None
            best_score = 0.0
            tkey = canonical_topic_key(str(t.get("topic_name") or ""))
            for pyq_key, pyq_row in pyq_by_key.items():
                score = _similarity(tkey, pyq_key)
                if score > best_score:
                    best_score = score
                    best_key = pyq_key
                    best_row = pyq_row
            if best_key and best_row is not None and best_score >= _MATCH_THRESHOLD:
                matched_pyq_keys.add(best_key)
                enriched.append(_apply_occurrence(t, best_row))
            else:
                enriched.append(_apply_occurrence(t, None))
        mod["topics"] = enriched

    # A PYQ topic often names a whole module ("Normalization") when the
    # syllabus lists only that module's sub-topics. Matching module names is
    # not inventing a module — the module comes from the syllabus.
    module_name_index = [
        (mod, canonical_topic_key(str(mod.get("module_name") or ""))) for mod in modules
    ]

    def _match_module_by_name(pyq_key: str) -> dict[str, Any] | None:
        best_mod: dict[str, Any] | None = None
        best_score = 0.0
        for mod, mkey in module_name_index:
            if not mkey:
                continue
            score = _similarity(pyq_key, mkey)
            if score > best_score:
                best_score = score
                best_mod = mod
        return best_mod if best_mod is not None and best_score >= _MATCH_THRESHOLD else None

    # Unmapped PYQ topics.
    unmapped: list[dict[str, Any]] = []
    for pyq_key, pyq_row in pyq_by_key.items():
        if pyq_key in matched_pyq_keys:
            continue
        match, score, review = match_pyq_topic_to_syllabus(
            str(pyq_row.get("topic") or ""),
            syllabus_topics,
        )
        if match and score >= _MATCH_THRESHOLD:
            # Late match into existing module topic (already enriched above via reverse).
            continue
        by_module_name = _match_module_by_name(pyq_key)
        if by_module_name is not None:
            topic_name = str(pyq_row.get("topic") or "")
            by_module_name["topics"].append(
                _apply_occurrence(
                    {
                        "topic_id": make_topic_id(topic_name),
                        "topic_name": topic_name,
                        "topic": topic_name,
                        "unit": by_module_name.get("display_name")
                        or by_module_name.get("module_name"),
                        "module_id": by_module_name.get("module_id"),
                        "module_number": by_module_name.get("module_number"),
                        "module_name": by_module_name.get("module_name"),
                        "from_syllabus": False,
                        "matched_by": "module_name",
                    },
                    pyq_row,
                )
            )
            continue
        item = {
            "topic_id": make_topic_id(str(pyq_row.get("topic") or pyq_key)),
            "topic_name": pyq_row.get("topic"),
            "topic": pyq_row.get("topic"),
            "unit": "Other / Unmapped Topics",
            "module_id": "m_unmapped",
            "module_number": None,
            "module_name": "Other / Unmapped Topics",
            "from_syllabus": False,
            "needs_review": bool(review),
            "match_confidence": round(score, 3),
        }
        unmapped.append(_apply_occurrence(item, pyq_row))
        if review:
            needs_review.append(
                {
                    "topic": pyq_row.get("topic"),
                    "best_score": round(score, 3),
                }
            )

    # Recalculate priority across the full set (syllabus + unmapped asked topics)
    # so unasked syllabus topics stay Low and asked ones stay relative.
    all_topics: list[dict[str, Any]] = []
    for mod in modules:
        all_topics.extend(mod.get("topics") or [])
    all_topics.extend(unmapped)

    asked = [t for t in all_topics if int(t.get("occurrence_count") or 0) > 0]
    max_freq = max((int(t.get("occurrence_count") or 0) for t in asked), default=1)
    max_marks = max(
        (
            float(t["total_marks"])
            for t in asked
            if t.get("total_marks") is not None
        ),
        default=0.0,
    )
    papers = max(1, int(analyzed_paper_count or 1))

    def _reprioritize(topic: dict[str, Any]) -> dict[str, Any]:
        occ = int(topic.get("occurrence_count") or 0)
        if occ <= 0:
            topic["priority"] = "Low"
            topic["importance"] = "Low"
            topic["priority_score"] = 0.0
            topic["asked"] = False
            return topic
        level, score = classify_priority(
            frequency=occ,
            max_frequency=max_freq,
            total_marks=topic.get("total_marks"),
            max_marks=max_marks if max_marks > 0 else None,
            paper_count=int(topic.get("paper_count") or 1),
            analyzed_papers=papers,
        )
        topic["priority"] = level
        topic["importance"] = level
        topic["priority_score"] = score
        topic["asked"] = True
        return topic

    for mod in modules:
        mod["topics"] = [_reprioritize(t) for t in (mod.get("topics") or [])]
        # Sort topics: priority then occurrence
        rank = {"High": 0, "Medium": 1, "Low": 2}
        mod["topics"].sort(
            key=lambda t: (
                0 if t.get("asked") else 1,
                rank.get(str(t.get("priority") or "Low"), 9),
                -int(t.get("occurrence_count") or 0),
                str(t.get("topic_name") or "").lower(),
            )
        )
        mod["topic_count"] = len(mod["topics"])
        mod["asked_topic_count"] = sum(1 for t in mod["topics"] if t.get("asked"))
        mod["high_priority_count"] = sum(
            1 for t in mod["topics"] if t.get("priority") == "High" and t.get("asked")
        )
        mod["question_occurrence"] = sum(int(t.get("occurrence_count") or 0) for t in mod["topics"])

    unmapped = [_reprioritize(t) for t in unmapped]
    unmapped.sort(
        key=lambda t: (
            {"High": 0, "Medium": 1, "Low": 2}.get(str(t.get("priority") or "Low"), 9),
            -int(t.get("occurrence_count") or 0),
        )
    )

    if not has_syllabus_modules:
        # No syllabus for this subject: PYQ topics are still fully usable, they
        # just are not module-grouped. Calling them "unmapped" would imply a
        # syllabus exists that they failed to match.
        for topic in unmapped:
            topic["unit"] = "General Topics"
            topic["module_id"] = "m_general"
            topic["module_number"] = 1
            topic["module_name"] = "General Topics"
            topic.pop("needs_review", None)
            topic.pop("match_confidence", None)
        modules = [
            {
                "module_id": "m_general",
                "module_number": 1,
                "module_name": "General Topics",
                "display_name": "General Topics",
                "is_fallback": True,
                "topics": unmapped,
                "topic_count": len(unmapped),
                "asked_topic_count": sum(1 for t in unmapped if t.get("asked")),
                "high_priority_count": sum(1 for t in unmapped if t.get("priority") == "High"),
                "question_occurrence": sum(int(t.get("occurrence_count") or 0) for t in unmapped),
            }
        ]
        needs_review = []
    elif unmapped:
        modules.append(
            {
                "module_id": "m_unmapped",
                "module_number": None,
                "module_name": "Other / Unmapped Topics",
                "display_name": "Other / Unmapped Topics",
                "is_unmapped": True,
                "topics": unmapped,
                "topic_count": len(unmapped),
                "asked_topic_count": len(unmapped),
                "high_priority_count": sum(1 for t in unmapped if t.get("priority") == "High"),
                "question_occurrence": sum(int(t.get("occurrence_count") or 0) for t in unmapped),
            }
        )

    flat_topics: list[dict[str, Any]] = []
    for mod in modules:
        flat_topics.extend(mod.get("topics") or [])

    real_modules = [
        m for m in modules if not m.get("is_unmapped") and not m.get("is_fallback")
    ]
    return {
        "modules": modules,
        "topics": flat_topics,  # flat list still available for backward compatibility
        "module_count": len(real_modules),
        "has_syllabus_modules": bool(real_modules),
        "needs_review": needs_review,
    }
