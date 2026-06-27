import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import BackgroundTasks, UploadFile

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.enums import ProcessingStatus
from app.repositories.document_repository import DocumentRepository
from app.repositories.stats_repository import StatsRepository
from app.services.file_service import FileService
from app.services.mappers import map_document_response
from app.services.subject_service import SubjectService
from app.utils.subject_detector import resolve_document_subject
from app.utils.text_extractor import extract_text

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        stats_repo: StatsRepository,
        file_service: FileService | None = None,
        subject_service: SubjectService | None = None,
    ) -> None:
        self.document_repo = document_repo
        self.stats_repo = stats_repo
        self.file_service = file_service or FileService()
        self.subject_service = subject_service

    async def upload_document(
        self,
        user_id: str,
        file: UploadFile,
        *,
        title: str | None,
        category: str,
        subject: str | None,
        exam_year: int | None,
        description: str | None,
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        if not file.filename:
            raise ValidationAppError("Filename is required")

        file_bytes = await file.read()
        if not file_bytes:
            raise ValidationAppError("Uploaded file is empty")

        file_type = self.file_service.detect_file_type(file.filename, file.content_type)
        allowed = set(settings.allowed_file_types_list)
        image_allowed = bool(allowed.intersection({"png", "jpg", "jpeg", "webp", "image"}))
        if file_type == "image" and not image_allowed:
            raise ValidationAppError(f"Image uploads are not allowed. Allowed: {settings.allowed_file_types}")
        if file_type != "image" and file_type not in allowed:
            raise ValidationAppError(f"File type not allowed. Allowed: {settings.allowed_file_types}")

        upload_result = await self.file_service.upload_file(file_bytes, file.filename, user_id)
        now = datetime.now(UTC)

        resolved_subject = resolve_document_subject(
            explicit_subject=subject,
            filename=file.filename,
            title=title or file.filename,
        )

        document = await self.document_repo.create(
            {
                "user_id": self.document_repo.to_object_id(user_id),
                "title": title or file.filename,
                "description": description,
                "category": category,
                "subject": resolved_subject,
                "exam_year": exam_year,
                "file_type": file_type,
                "file_url": upload_result["file_url"],
                "file_public_id": upload_result["file_public_id"],
                "file_size_bytes": upload_result.get("file_size_bytes", len(file_bytes)),
                "extracted_text": None,
                "page_count": None,
                "status": ProcessingStatus.PROCESSING,
                "error_message": None,
                "tags": [],
                "created_at": now,
                "updated_at": now,
            }
        )

        await self.stats_repo.increment_field(user_id, "documents_count")
        await self.stats_repo.add_activity(
            user_id,
            {
                "type": "document_upload",
                "ref_id": str(document["_id"]),
                "title": document["title"],
                "timestamp": now,
            },
        )

        background_tasks.add_task(
            self._process_document_text,
            str(document["_id"]),
            user_id,
            file_bytes,
            file_type,
            resolved_subject,
        )

        if self.subject_service and resolved_subject and category == "pyq":
            await self.subject_service.on_pyq_uploaded(user_id, resolved_subject)

        return map_document_response(document)

    async def upload_documents_batch(
        self,
        user_id: str,
        files: list[UploadFile],
        *,
        category: str,
        subject: str | None,
        exam_year: int | None,
        background_tasks: BackgroundTasks,
    ) -> list[dict[str, Any]]:
        if not files:
            raise ValidationAppError("At least one file is required")
        if len(files) > settings.max_pyq_documents_per_analysis:
            raise ValidationAppError(
                f"Maximum {settings.max_pyq_documents_per_analysis} files allowed per upload"
            )

        uploaded: list[dict[str, Any]] = []
        for file in files:
            title = file.filename.rsplit(".", 1)[0] if file.filename and "." in file.filename else file.filename
            per_file_subject = resolve_document_subject(
                explicit_subject=subject,
                filename=file.filename,
                title=title,
            )
            doc = await self.upload_document(
                user_id,
                file,
                title=title,
                category=category,
                subject=per_file_subject,
                exam_year=exam_year,
                description=None,
                background_tasks=background_tasks,
            )
            uploaded.append(doc)
        return uploaded

    async def _process_document_text(
        self,
        document_id: str,
        user_id: str,
        file_bytes: bytes,
        file_type: str,
        subject: str | None = None,
    ) -> None:
        try:
            result = extract_text(file_bytes, file_type)
            if not result["text"].strip():
                raise ValidationAppError(
                    "No text could be extracted from this file. "
                    "Ensure the PDF contains selectable text (not a scanned image-only PDF)."
                )
            await self.document_repo.update(
                document_id,
                user_id,
                {
                    "extracted_text": result["text"],
                    "page_count": result["page_count"],
                    "status": ProcessingStatus.READY,
                    "error_message": None,
                },
            )
        except Exception as exc:
            logger.error("Text extraction failed for document %s: %s", document_id, exc)
            await self.document_repo.update(
                document_id,
                user_id,
                {
                    "status": ProcessingStatus.FAILED,
                    "error_message": str(exc),
                },
            )

    async def list_documents(
        self,
        user_id: str,
        *,
        page: int,
        limit: int,
        category: str | None = None,
        subject: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * limit
        documents = await self.document_repo.list_by_user(
            user_id,
            skip=skip,
            limit=limit,
            category=category,
            subject=subject,
            status=status,
            search=search,
        )
        total = await self.document_repo.count_by_user(user_id)
        return [map_document_response(doc) for doc in documents], total

    async def get_document(self, document_id: str, user_id: str) -> dict[str, Any]:
        document = await self.document_repo.get_by_id_and_user(document_id, user_id)
        if not document:
            raise NotFoundError("Document not found")
        return map_document_response(document)

    async def get_document_status(self, document_id: str, user_id: str) -> dict[str, Any]:
        document = await self.get_document(document_id, user_id)
        return {
            "id": document["id"],
            "status": document["status"],
            "error_message": document.get("error_message"),
        }

    async def update_document(
        self,
        document_id: str,
        user_id: str,
        update_data: dict[str, Any],
    ) -> dict[str, Any]:
        filtered = {k: v for k, v in update_data.items() if v is not None}
        if not filtered:
            raise ValidationAppError("No fields to update")

        document = await self.document_repo.update(document_id, user_id, filtered)
        if not document:
            raise NotFoundError("Document not found")
        return map_document_response(document)

    async def delete_document(self, document_id: str, user_id: str) -> None:
        document = await self.document_repo.get_by_id_and_user(document_id, user_id)
        if not document:
            raise NotFoundError("Document not found")

        try:
            await self.file_service.delete_file(document["file_public_id"])
        except Exception:
            logger.warning("Failed to delete Cloudinary file for document %s", document_id)

        deleted = await self.document_repo.delete(document_id, user_id)
        if not deleted:
            raise NotFoundError("Document not found")

        await self.stats_repo.increment_field(user_id, "documents_count", -1)

    async def clear_documents(self, user_id: str, *, category: str | None = None) -> int:
        """Delete all of a user's uploaded documents (optionally one category)."""
        docs = await self.document_repo.list_all_by_user(user_id, category=category)
        for doc in docs:
            public_id = doc.get("file_public_id")
            if public_id:
                try:
                    await self.file_service.delete_file(public_id)
                except Exception:
                    logger.warning("Failed to delete stored file for document %s", doc.get("_id"))

        deleted = await self.document_repo.delete_all_by_user(user_id, category=category)
        if deleted:
            await self.stats_repo.increment_field(user_id, "documents_count", -deleted)
        return deleted
