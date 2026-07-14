"""
PDF / document text extraction and one-time chunk caching.

Performance: extract once on upload, store chunks in MongoDB, reuse for RAG/analysis.
CPU-bound parsing runs in a thread pool via asyncio.to_thread().
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.services.ai.base_provider import chunk_text
from app.services.pipeline.notes_pipeline import NotesPipeline
from app.utils.text_extractor import extract_text

logger = logging.getLogger(__name__)

# Smaller chunks = faster RAG scoring and smaller LLM prompts.
RAG_CHUNK_SIZE = 1200
RAG_CHUNK_OVERLAP = 150
MAX_STORED_CHUNKS = 80


def build_text_chunks(text: str) -> list[str]:
    """Split cleaned document text into cached chunks (computed once per upload)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    chunks = chunk_text(cleaned, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP)
    return chunks[:MAX_STORED_CHUNKS]


def extract_and_chunk_sync(file_bytes: bytes, file_type: str) -> dict[str, Any]:
    """
    Synchronous extract + preprocess + chunk (runs in thread pool).
    Called once per document upload — never re-reads the PDF file afterward.
    """
    result = extract_text(file_bytes, file_type)
    raw_text = result.get("text") or ""
    if not raw_text.strip():
        return {
            "text": "",
            "page_count": result.get("page_count", 0),
            "chunks": [],
        }

    pipeline = NotesPipeline()
    preprocessed = pipeline.preprocess(raw_text)
    cleaned_text = preprocessed.cleaned_text or raw_text
    chunks = build_text_chunks(cleaned_text)

    logger.info(
        "PDF processed: pages=%s chars=%d chunks=%d",
        result.get("page_count"),
        len(cleaned_text),
        len(chunks),
    )
    return {
        "text": cleaned_text,
        "page_count": result.get("page_count", 0),
        "chunks": chunks,
    }


async def extract_and_chunk_async(file_bytes: bytes, file_type: str) -> dict[str, Any]:
    """Non-blocking wrapper — keeps the event loop free during OCR/PDF parsing."""
    return await asyncio.to_thread(extract_and_chunk_sync, file_bytes, file_type)
