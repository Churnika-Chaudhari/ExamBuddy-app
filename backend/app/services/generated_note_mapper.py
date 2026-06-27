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
        "subject": doc.get("subject"),
        "unit": doc.get("unit"),
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
