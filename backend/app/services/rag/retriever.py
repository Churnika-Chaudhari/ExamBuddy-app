"""
RAG retrieval from uploaded PDFs, PYQs, and study materials.
Priority: analysis-linked documents → other user documents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.services.ai.base_provider import chunk_text
from app.services.ai.notes_sanitizer import sanitize_rag_passage
from app.utils.subject_detector import normalize_subject_name, resolve_document_subject
from app.utils.watermark_filter import remove_watermarks_from_text

_CHUNK_SIZE = 1200
_CHUNK_OVERLAP = 150
_MAX_CHUNKS = 8
_MAX_CONTEXT_CHARS = 10_000

# Retrieval priority by source type: user notes first, then PYQs, then study
# materials, then anything else. AI knowledge is only used when nothing is found.
_CATEGORY_BOOST: dict[str, float] = {
    "notes": 24.0,
    "study_material": 12.0,
    "pyq": 8.0,
    "other": 2.0,
    "document": 2.0,
}


@dataclass
class RetrievedChunk:
    text: str
    source_title: str
    source_category: str
    score: float
    document_id: str


def _doc_subject_key(doc: dict[str, Any]) -> str:
    """Resolved, normalised subject for a document (handles unset subject field)."""
    resolved = resolve_document_subject(
        explicit_subject=doc.get("subject"),
        filename=doc.get("title"),
        title=doc.get("title"),
    )
    return normalize_subject_name(resolved or "").strip().lower()


def _topic_terms(topic: str) -> list[str]:
    terms = [topic.lower().strip()]
    words = [w for w in re.split(r"[\s\-_/]+", topic.lower()) if len(w) > 2]
    terms.extend(words)
    return list(dict.fromkeys(terms))


def _score_chunk(chunk: str, terms: list[str], topic: str) -> float:
    lower = chunk.lower()
    score = 0.0
    topic_lower = topic.lower()

    if topic_lower in lower:
        score += 25.0

    for term in terms:
        count = lower.count(term)
        if count:
            score += count * (4.0 if len(term) > 5 else 2.0)

    exam_signals = ("explain", "define", "describe", "write", "marks", "question", "?")
    for signal in exam_signals:
        if signal in lower and any(t in lower for t in terms):
            score += 1.5

    if re.search(r"(diagram|figure|architecture|flow|process|steps?)", lower):
        score += 2.0

    return score


def _extract_topic_passages(text: str, topic: str, terms: list[str]) -> list[str]:
    """Pull lines/paragraphs that mention the topic from raw document text."""
    passages: list[str] = []
    topic_lower = topic.lower()

    for paragraph in re.split(r"\n{2,}", text):
        p = paragraph.strip()
        if len(p) < 40:
            continue
        pl = p.lower()
        if topic_lower in pl or any(t in pl for t in terms):
            passages.append(p[:2500])

    for line in text.splitlines():
        line = line.strip()
        if len(line) < 20:
            continue
        ll = line.lower()
        if (topic_lower in ll or any(t in ll for t in terms)) and (
            "?" in line
            or re.search(r"\b(explain|define|describe|write|discuss)\b", ll)
        ):
            passages.append(line[:1200])

    return passages[:20]


class DocumentRetriever:
    """Retrieve relevant chunks from user-uploaded study materials."""

    def __init__(self, document_repo: Any) -> None:
        self.document_repo = document_repo

    async def _candidate_documents(
        self,
        user_id: str,
        *,
        subject: str | None,
        analysis_document_ids: list[str] | None,
    ) -> list[dict[str, Any]]:
        """All READY documents to search, scoped to the subject when provided."""
        all_ready = await self.document_repo.list_by_user(
            user_id, skip=0, limit=300, status="ready"
        )

        if subject:
            target = normalize_subject_name(subject).strip().lower()
            scoped = [d for d in all_ready if _doc_subject_key(d) == target]
            # Keep any analysis-linked docs even if their subject label differs.
            if analysis_document_ids:
                analysis_set = set(analysis_document_ids)
                scoped_ids = {str(d["_id"]) for d in scoped}
                for d in all_ready:
                    if str(d["_id"]) in analysis_set and str(d["_id"]) not in scoped_ids:
                        scoped.append(d)
            if scoped:
                return scoped

        return all_ready

    async def retrieve_for_topic(
        self,
        user_id: str,
        topic: str,
        *,
        subject: str | None = None,
        analysis_document_ids: list[str] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Retrieve relevant content for a topic across ALL of the subject's
        uploaded documents. Sources are prioritised: user notes > PYQs > study
        materials > anything else; analysis-linked docs get an extra boost.
        """
        terms = _topic_terms(topic)
        docs = await self._candidate_documents(
            user_id, subject=subject, analysis_document_ids=analysis_document_ids
        )
        analysis_set = set(analysis_document_ids or [])

        ranked: list[RetrievedChunk] = []

        for doc in docs:
            title = doc.get("title") or "Untitled"
            category = doc.get("category") or "document"
            doc_id = str(doc["_id"])
            boost = _CATEGORY_BOOST.get(category, 2.0)
            if doc_id in analysis_set:
                boost += 6.0

            stored_chunks: list[str] = doc.get("text_chunks") or []
            if stored_chunks:
                for chunk in stored_chunks:
                    if not chunk.strip():
                        continue
                    score = _score_chunk(chunk, terms, topic) + boost
                    if score >= 2.0:
                        ranked.append(
                            RetrievedChunk(chunk, title, category, score, doc_id)
                        )
                continue

            raw = doc.get("extracted_text") or ""
            if not raw.strip():
                continue
            text = remove_watermarks_from_text(raw)

            for passage in _extract_topic_passages(text, topic, terms):
                score = _score_chunk(passage, terms, topic) + boost
                if score > 0:
                    ranked.append(
                        RetrievedChunk(passage, title, category, score, doc_id)
                    )

            for chunk in chunk_text(text, _CHUNK_SIZE, _CHUNK_OVERLAP):
                score = _score_chunk(chunk, terms, topic) + boost
                if score >= 3.0:
                    ranked.append(
                        RetrievedChunk(chunk, title, category, score, doc_id)
                    )

        ranked.sort(key=lambda c: -c.score)
        seen_text: set[str] = set()
        selected: list[RetrievedChunk] = []
        for chunk in ranked:
            key = chunk.text[:200].lower()
            if key in seen_text:
                continue
            seen_text.add(key)
            selected.append(chunk)
            if len(selected) >= _MAX_CHUNKS:
                break

        if not selected:
            return "", []

        parts: list[str] = []
        seen_sources: set[str] = set()
        sources: list[dict[str, Any]] = []
        total = 0

        for chunk in selected:
            cleaned = sanitize_rag_passage(chunk.text.strip())
            if len(cleaned) < 40:
                continue
            block = cleaned
            if total + len(block) > _MAX_CONTEXT_CHARS:
                break
            parts.append(block)
            total += len(block)
            # One entry per source document for a clean "Generated from" list.
            if chunk.document_id not in seen_sources:
                seen_sources.add(chunk.document_id)
                sources.append(
                    {
                        "document_id": chunk.document_id,
                        "title": chunk.source_title,
                        "category": chunk.source_category,
                        "relevance_score": round(chunk.score, 2),
                    }
                )

        context = "\n\n---\n\n".join(parts) if parts else ""
        return context, sources
