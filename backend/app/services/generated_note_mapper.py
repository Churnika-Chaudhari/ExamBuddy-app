from __future__ import annotations

from typing import Any

from app.services.mappers import map_document_response


def map_generated_note(doc: dict[str, Any], *, cached: bool = False) -> dict[str, Any]:
    mapped = map_document_response(doc)
    analysis_id = doc.get("analysis_id")
    return {
        "id": mapped.get("id"),
        "user_id": mapped.get("user_id"),
        "topic": doc.get("topic", ""),
        "notes": doc.get("notes", "") or "",
        "summary": doc.get("summary"),
        "structured_notes": doc.get("structured_notes"),
        "subject": doc.get("subject"),
        "subject_id": str(doc["subject_id"]) if doc.get("subject_id") else None,
        "unit": doc.get("unit"),
        "module_id": doc.get("module_id"),
        "module_name": doc.get("module_name"),
        "module_number": doc.get("module_number"),
        "topic_id": doc.get("topic_id"),
        "frequency": doc.get("frequency"),
        "analysis_id": str(analysis_id) if analysis_id else None,
        "is_saved": doc.get("is_saved", False),
        "cached": cached,
        "ai_metadata": doc.get("ai_metadata"),
        "rag_sources": doc.get("rag_sources") or (doc.get("ai_metadata") or {}).get("rag_sources"),
        "generated_at": mapped.get("generated_at") or mapped.get("created_at"),
        "created_at": mapped.get("created_at"),
        "updated_at": mapped.get("updated_at"),
    }
