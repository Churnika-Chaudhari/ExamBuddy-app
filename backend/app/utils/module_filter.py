"""Filter syllabus modules / PYQ topics by one or more module IDs."""

from __future__ import annotations

from typing import Any


def parse_module_ids(raw: str | list[str] | None) -> list[str]:
    """Parse comma-separated or list module IDs, preserving order and uniqueness."""
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",")]
    else:
        parts = [str(p).strip() for p in raw]
    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        if not part or part in seen:
            continue
        seen.add(part)
        ordered.append(part)
    return ordered


def _topic_key(topic: dict[str, Any]) -> str:
    return str(topic.get("topic_id") or topic.get("topic_name") or topic.get("topic") or "").strip().lower()


def _is_asked(topic: dict[str, Any]) -> bool:
    if topic.get("asked") is True:
        return True
    occ = topic.get("occurrence_count")
    if occ is None:
        occ = topic.get("frequency") or 0
    try:
        return int(occ) > 0
    except (TypeError, ValueError):
        return False


def _dedupe_topics(topics: list[dict[str, Any]], seen: set[str]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    for topic in topics:
        key = _topic_key(topic)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(topic)
    return unique


def filter_module_tree(
    modules: list[dict[str, Any]] | None,
    topics: list[dict[str, Any]] | None = None,
    selected_ids: list[str] | None = None,
    include_unmapped: bool | None = None,
) -> dict[str, Any]:
    """
    Return modules/topics where module_id IN selected_ids (SQL IN equivalent).

    - selected_ids empty/None → all modules (All Modules)
    - include_unmapped False → drop m_unmapped even when All Modules
    - include_unmapped True → keep unmapped if it is in the selection (or all)
    - include_unmapped None → keep unmapped only when selected or All Modules
    Deduplicates topics across selected modules.
    """
    source_modules = list(modules or [])
    by_id = {str(m.get("module_id")): m for m in source_modules if m.get("module_id")}

    if selected_ids:
        requested = parse_module_ids(selected_ids)
        all_modules = False
    else:
        requested = [str(m.get("module_id")) for m in source_modules if m.get("module_id")]
        all_modules = True

    if include_unmapped is False:
        requested = [mid for mid in requested if mid != "m_unmapped"]
    elif include_unmapped is True and "m_unmapped" in by_id and "m_unmapped" not in requested:
        requested.append("m_unmapped")

    seen: set[str] = set()
    filtered_modules: list[dict[str, Any]] = []
    empty_modules: list[str] = []

    for mid in requested:
        mod = by_id.get(mid)
        if not mod:
            continue
        unique_topics = _dedupe_topics(list(mod.get("topics") or []), seen)
        asked = [t for t in unique_topics if _is_asked(t)]
        display = str(mod.get("display_name") or mod.get("module_name") or mid)
        clone = {
            **mod,
            "topics": unique_topics,
            "topic_count": len(unique_topics),
            "asked_topic_count": len(asked),
            "pyq_topics": asked,
        }
        filtered_modules.append(clone)
        if not asked:
            empty_modules.append(display)

    flat_topics = [t for mod in filtered_modules for t in (mod.get("topics") or [])]
    if not filtered_modules and topics:
        # Fallback: filter a flat topic list when module objects are missing.
        id_set = set(requested)
        flat_topics = _dedupe_topics(
            [t for t in topics if not id_set or str(t.get("module_id") or "") in id_set],
            set(),
        )

    return {
        "modules": filtered_modules,
        "topics": flat_topics,
        "selected_module_ids": [str(m.get("module_id")) for m in filtered_modules],
        "empty_modules": empty_modules,
        "all_modules": all_modules and include_unmapped is not False,
    }
