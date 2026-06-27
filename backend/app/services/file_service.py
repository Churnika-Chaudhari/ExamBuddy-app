import logging
import uuid
from pathlib import Path
from typing import Any

import cloudinary
import cloudinary.uploader
import httpx

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError, ValidationAppError

logger = logging.getLogger(__name__)
settings = get_settings()

UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "uploads"


class FileService:
    def __init__(self) -> None:
        if settings.cloudinary_cloud_name:
            cloudinary.config(
                cloud_name=settings.cloudinary_cloud_name,
                api_key=settings.cloudinary_api_key,
                api_secret=settings.cloudinary_api_secret,
                secure=True,
            )

    @property
    def uses_local_storage(self) -> bool:
        return not settings.cloudinary_cloud_name

    def _upload_local(self, file_bytes: bytes, filename: str, user_id: str) -> dict[str, Any]:
        user_dir = UPLOAD_ROOT / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = user_dir / safe_name
        file_path.write_bytes(file_bytes)
        logger.info("Saved file locally: %s", file_path)
        return {
            "file_url": f"local://{file_path.as_posix()}",
            "file_public_id": f"local:{file_path.as_posix()}",
            "file_size_bytes": len(file_bytes),
            "format": filename.rsplit(".", 1)[-1].lower(),
        }

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        user_id: str,
        folder: str = "smartstudy/documents",
    ) -> dict[str, Any]:
        if len(file_bytes) > settings.max_upload_size_bytes:
            raise ValidationAppError(
                f"File size exceeds {settings.max_upload_size_mb}MB limit"
            )

        if self.uses_local_storage:
            logger.warning("Cloudinary not configured — using local file storage")
            return self._upload_local(file_bytes, filename, user_id)

        try:
            result = cloudinary.uploader.upload(
                file_bytes,
                folder=folder,
                resource_type="auto",
                public_id=f"{folder}/{filename.rsplit('.', 1)[0]}",
                overwrite=True,
            )
            return {
                "file_url": result.get("secure_url") or result.get("url"),
                "file_public_id": result.get("public_id"),
                "file_size_bytes": result.get("bytes", len(file_bytes)),
                "format": result.get("format"),
            }
        except Exception as exc:
            logger.error("Cloudinary upload failed: %s", exc)
            raise ExternalServiceError("File upload to Cloudinary failed") from exc

    async def delete_file(self, public_id: str) -> None:
        if public_id.startswith("local:"):
            path = Path(public_id.removeprefix("local:"))
            if path.exists():
                path.unlink()
            return

        if not settings.cloudinary_cloud_name:
            return

        try:
            cloudinary.uploader.destroy(public_id, resource_type="auto")
        except Exception as exc:
            logger.error("Cloudinary delete failed: %s", exc)
            raise ExternalServiceError("Failed to delete file from Cloudinary") from exc

    async def download_file(self, file_url: str) -> bytes:
        if file_url.startswith("local://"):
            path = Path(file_url.removeprefix("local://"))
            return path.read_bytes()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(file_url)
                response.raise_for_status()
                return response.content
        except Exception as exc:
            logger.error("File download failed: %s", exc)
            raise ExternalServiceError("Failed to download file") from exc

    @staticmethod
    def detect_file_type(filename: str, content_type: str | None = None) -> str:
        extension = filename.rsplit(".", 1)[-1].lower()
        mapping = {
            "pdf": "pdf",
            "docx": "docx",
            "doc": "docx",
            "png": "image",
            "jpg": "image",
            "jpeg": "image",
            "webp": "image",
        }
        if extension in mapping:
            return mapping[extension]
        if content_type:
            if "pdf" in content_type:
                return "pdf"
            if "word" in content_type or "docx" in content_type:
                return "docx"
            if "image" in content_type:
                return "image"
        raise ValidationAppError(f"Unsupported file type: {filename}")
