from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from app.api.deps import get_notes_service
from app.core.dependencies import get_current_user
from app.core.responses import paginated_response, success_response
from app.models.enums import NoteType
from app.schemas.common import PaginationParams
from app.schemas.notes import (
    NoteGenerateRequest,
    NoteSimplifyRequest,
    NoteUpdateRequest,
    TopicNoteGenerateRequest,
)
from app.services.notes_service import NotesService

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI notes — single topic (cached) or batch from analysis",
)
async def generate_notes(
    payload: NoteGenerateRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    data = await notes_service.generate_notes(
        str(current_user["_id"]),
        analysis_id=payload.analysis_id,
        topics=payload.topics,
        title=payload.title,
        subject=payload.subject,
        topic=payload.topic,
        unit=payload.unit,
        frequency=payload.frequency,
        regenerate=payload.regenerate,
    )
    message = (
        "Topic notes ready"
        if payload.topic
        else "Notes generated successfully"
    )
    return success_response(data, message)


@router.post(
    "/topic/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Generate AI study notes for a single topic (with smart caching)",
)
async def generate_topic_notes(
    payload: TopicNoteGenerateRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    data = await notes_service.generate_topic_note(
        str(current_user["_id"]),
        payload.topic,
        analysis_id=payload.analysis_id,
        subject=payload.subject,
        unit=payload.unit,
        frequency=payload.frequency,
        regenerate=payload.regenerate,
    )
    msg = "Cached notes returned" if data.get("cached") else "Notes generated successfully"
    return success_response(data, msg)


@router.post(
    "/topic/regenerate",
    status_code=status.HTTP_201_CREATED,
    summary="Force regenerate AI study notes for a topic",
)
async def regenerate_topic_notes(
    payload: TopicNoteGenerateRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    data = await notes_service.generate_topic_note(
        str(current_user["_id"]),
        payload.topic,
        analysis_id=payload.analysis_id,
        subject=payload.subject,
        unit=payload.unit,
        frequency=payload.frequency,
        regenerate=True,
    )
    return success_response(data, "Notes regenerated successfully")


@router.get("/topic/status", summary="Check if cached notes exist for a topic")
async def topic_notes_status(
    topic: Annotated[str, Query(min_length=1)],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
    analysis_id: str | None = None,
):
    data = await notes_service.get_topic_cache_status(
        str(current_user["_id"]), topic, analysis_id=analysis_id
    )
    return success_response(data)


@router.get("/generated", summary="List per-topic generated study notes")
async def list_generated_notes(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
    pagination: Annotated[PaginationParams, Depends()],
    analysis_id: str | None = None,
):
    notes, total = await notes_service.list_generated_notes(
        str(current_user["_id"]),
        page=pagination.page,
        limit=pagination.limit,
        analysis_id=analysis_id,
    )
    return paginated_response(notes, pagination.page, pagination.limit, total)


@router.get(
    "/generated/{note_id}/export/pdf",
    summary="Download per-topic study notes as PDF",
)
async def export_generated_note_pdf(
    note_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    pdf_bytes, filename = await notes_service.export_generated_note_pdf(
        note_id, str(current_user["_id"])
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/generated/{note_id}", summary="Get per-topic generated note by ID")
async def get_generated_note(
    note_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    data = await notes_service.get_generated_note(note_id, str(current_user["_id"]))
    return success_response(data)


@router.patch("/generated/{note_id}/save", summary="Save or unsave generated topic notes")
async def save_generated_note(
    note_id: str,
    is_saved: Annotated[bool, Query()],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    data = await notes_service.save_generated_note(
        note_id, str(current_user["_id"]), is_saved
    )
    return success_response(data, "Note saved" if is_saved else "Note unsaved")


@router.post(
    "/simplify",
    status_code=status.HTTP_201_CREATED,
    summary="Simplify uploaded notes or document content",
)
async def simplify_notes(
    payload: NoteSimplifyRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    data = await notes_service.simplify_notes(
        str(current_user["_id"]),
        document_id=payload.document_id,
        text=payload.text,
        title=payload.title,
    )
    return success_response(data, "Notes simplified successfully")


@router.get("", summary="List user notes")
async def list_notes(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
    pagination: Annotated[PaginationParams, Depends()],
    note_type: NoteType | None = None,
    is_favorite: bool | None = None,
):
    notes, total = await notes_service.list_notes(
        str(current_user["_id"]),
        page=pagination.page,
        limit=pagination.limit,
        note_type=note_type.value if note_type else None,
        is_favorite=is_favorite,
    )
    return paginated_response(notes, pagination.page, pagination.limit, total)


@router.delete("", summary="Clear all notes (batch + per-topic AI notes)")
async def clear_notes(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    deleted = await notes_service.clear_notes(str(current_user["_id"]))
    return success_response({"deleted": deleted, "message": "Notes cleared"})


@router.get("/{note_id}/export/pdf", summary="Download note as PDF")
async def export_note_pdf(
    note_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    pdf_bytes, filename = await notes_service.export_note_pdf(
        note_id, str(current_user["_id"])
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{note_id}", summary="Get note by ID")
async def get_note(
    note_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    data = await notes_service.get_note(note_id, str(current_user["_id"]))
    return success_response(data)


@router.patch("/{note_id}", summary="Update note")
async def update_note(
    note_id: str,
    payload: NoteUpdateRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    data = await notes_service.update_note(note_id, str(current_user["_id"]), payload.model_dump())
    return success_response(data, "Note updated")


@router.delete("/{note_id}", summary="Delete note")
async def delete_note(
    note_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    notes_service: Annotated[NotesService, Depends(get_notes_service)],
):
    await notes_service.delete_note(note_id, str(current_user["_id"]))
    return success_response({"message": "Note deleted successfully"})
