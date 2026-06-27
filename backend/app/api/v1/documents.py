from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status

from app.api.deps import get_document_service
from app.core.dependencies import get_current_user
from app.core.responses import paginated_response, success_response
from app.models.enums import DocumentCategory
from app.schemas.common import PaginationParams
from app.schemas.document import DocumentUpdateRequest
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload PDF, DOCX, or image document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    file: UploadFile = File(..., description="PDF, DOCX, or image file"),
    title: str | None = Form(default=None),
    category: DocumentCategory = Form(default=DocumentCategory.PYQ),
    subject: str | None = Form(default=None),
    exam_year: int | None = Form(default=None),
    description: str | None = Form(default=None),
):
    data = await document_service.upload_document(
        str(current_user["_id"]),
        file,
        title=title,
        category=category.value,
        subject=subject,
        exam_year=exam_year,
        description=description,
        background_tasks=background_tasks,
    )
    return success_response({"document": data}, "Document uploaded successfully")


@router.post(
    "/upload-batch",
    status_code=status.HTTP_201_CREATED,
    summary="Upload multiple PDF/DOCX documents in one request",
)
async def upload_documents_batch(
    background_tasks: BackgroundTasks,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    files: list[UploadFile] = File(..., description="Multiple PDF or DOCX files"),
    category: DocumentCategory = Form(default=DocumentCategory.PYQ),
    subject: str | None = Form(default=None),
    exam_year: int | None = Form(default=None),
):
    documents = await document_service.upload_documents_batch(
        str(current_user["_id"]),
        files,
        category=category.value,
        subject=subject,
        exam_year=exam_year,
        background_tasks=background_tasks,
    )
    return success_response(
        {"documents": documents, "count": len(documents)},
        f"{len(documents)} documents uploaded successfully",
    )


@router.get("", summary="List user documents")
async def list_documents(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    pagination: Annotated[PaginationParams, Depends()],
    category: DocumentCategory | None = None,
    subject: str | None = None,
    status: str | None = None,
    search: str | None = None,
):
    documents, total = await document_service.list_documents(
        str(current_user["_id"]),
        page=pagination.page,
        limit=pagination.limit,
        category=category.value if category else None,
        subject=subject,
        status=status,
        search=search,
    )
    return paginated_response(documents, pagination.page, pagination.limit, total)


@router.delete("", summary="Clear all uploaded documents")
async def clear_documents(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    category: DocumentCategory | None = None,
):
    deleted = await document_service.clear_documents(
        str(current_user["_id"]),
        category=category.value if category else None,
    )
    return success_response({"deleted": deleted, "message": "Documents cleared"})


@router.get("/{document_id}", summary="Get document by ID")
async def get_document(
    document_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
):
    data = await document_service.get_document(document_id, str(current_user["_id"]))
    return success_response(data)


@router.get("/{document_id}/status", summary="Get document processing status")
async def get_document_status(
    document_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
):
    data = await document_service.get_document_status(document_id, str(current_user["_id"]))
    return success_response(data)


@router.patch("/{document_id}", summary="Update document metadata")
async def update_document(
    document_id: str,
    payload: DocumentUpdateRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
):
    data = await document_service.update_document(
        document_id,
        str(current_user["_id"]),
        payload.model_dump(),
    )
    return success_response(data, "Document updated")


@router.delete("/{document_id}", summary="Delete document")
async def delete_document(
    document_id: str,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
):
    await document_service.delete_document(document_id, str(current_user["_id"]))
    return success_response({"message": "Document deleted successfully"})
