from typing import Any

from app.db.mongodb import serialize_doc


def map_user_response(user: dict[str, Any]) -> dict[str, Any]:
    serialized = serialize_doc(user)
    if not serialized:
        return {}
    return {
        "id": serialized["id"],
        "email": serialized["email"],
        "full_name": serialized.get("full_name", ""),
        "avatar_url": serialized.get("avatar_url"),
        "institution": serialized.get("institution"),
        "course": serialized.get("course"),
        "preferences": serialized.get(
            "preferences",
            {"ai_provider": "openai", "theme": "light", "notifications": True},
        ),
        "is_active": serialized.get("is_active", True),
        "created_at": serialized.get("created_at"),
        "updated_at": serialized.get("updated_at"),
    }


def map_quiz_response(quiz: dict[str, Any]) -> dict[str, Any]:
    serialized = serialize_doc(quiz)
    if not serialized:
        return {}
    if "source_notes_id" in quiz and quiz.get("source_notes_id"):
        serialized["source_notes_id"] = str(quiz["source_notes_id"])
    if "source_analysis_id" in quiz and quiz.get("source_analysis_id"):
        serialized["source_analysis_id"] = str(quiz["source_analysis_id"])
    if "quiz_id" in quiz and quiz.get("quiz_id"):
        serialized["quiz_id"] = str(quiz["quiz_id"])
    subject = (quiz.get("subject") or "").strip()
    if subject:
        serialized["subject"] = subject
    title = (quiz.get("title") or "").strip()
    serialized["title"] = title or (f"{subject} Quiz" if subject else "Generated Quiz")
    if quiz.get("difficulty") is not None:
        serialized["difficulty"] = str(quiz["difficulty"])
    if quiz.get("quiz_type") is not None:
        serialized["quiz_type"] = str(quiz["quiz_type"])
    return serialized


def map_document_response(document: dict[str, Any]) -> dict[str, Any]:
    serialized = serialize_doc(document)
    if not serialized:
        return {}
    if "document_ids" not in serialized and "_document_ids" in document:
        serialized["document_ids"] = [str(doc_id) for doc_id in document.get("document_ids", [])]
    if "document_ids" in document and isinstance(document["document_ids"], list):
        serialized["document_ids"] = [str(doc_id) for doc_id in document["document_ids"]]
    if "source_id" in document and document["source_id"]:
        serialized["source_id"] = str(document["source_id"])
    if "source_notes_id" in document and document.get("source_notes_id"):
        serialized["source_notes_id"] = str(document["source_notes_id"])
    if "source_analysis_id" in document and document.get("source_analysis_id"):
        serialized["source_analysis_id"] = str(document["source_analysis_id"])
    if "quiz_id" in document and document.get("quiz_id"):
        serialized["quiz_id"] = str(document["quiz_id"])
    return serialized
