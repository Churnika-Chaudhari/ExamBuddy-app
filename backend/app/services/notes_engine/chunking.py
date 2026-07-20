"""Semantic-ish chunking and context cleaning for exam notes generation."""

from __future__ import annotations

import re
from typing import Any

from app.services.ai.notes_sanitizer import sanitize_rag_passage

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
_NOISE_LINE = re.compile(
    r"^\s*(page\s*\d+|subject\s*code|max\.?\s*marks|time\s*:|q\d+\.|\[\d+\s*marks?\])",
    re.I,
)


def clean_study_text(text: str) -> str:
    """OCR/text cleaning stage — drop paper scaffolding and empty lines."""
    if not text:
        return ""
    cleaned = sanitize_rag_passage(text)
    lines: list[str] = []
    for raw in cleaned.splitlines():
        line = raw.strip()
        if not line or _NOISE_LINE.match(line):
            continue
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def semantic_chunks(
    text: str,
    *,
    topic: str = "",
    max_chunks: int = 10,
    target_chars: int = 900,
) -> list[str]:
    """
    Split cleaned study material into topic-biased chunks.

    Prefer paragraphs that mention the topic; pack nearby sentences to ~target_chars.
    """
    cleaned = clean_study_text(text)
    if not cleaned:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    if not paragraphs:
        paragraphs = [cleaned]

    topic_terms = [t for t in re.split(r"\W+", topic.lower()) if len(t) > 2]
    scored: list[tuple[int, str]] = []
    for para in paragraphs:
        score = 0
        lower = para.lower()
        for term in topic_terms:
            if term in lower:
                score += 3
        if "?" in para or lower.startswith(("explain", "define", "compare", "differentiate")):
            score += 1
        scored.append((score, para))

    scored.sort(key=lambda item: (-item[0], -len(item[1])))

    chunks: list[str] = []
    for _, para in scored:
        if len(chunks) >= max_chunks:
            break
        if len(para) <= target_chars:
            chunks.append(para)
            continue
        sentences = _SENTENCE_SPLIT.split(para)
        buf = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if buf and len(buf) + len(sentence) + 1 > target_chars:
                chunks.append(buf)
                buf = sentence
                if len(chunks) >= max_chunks:
                    break
            else:
                buf = f"{buf} {sentence}".strip() if buf else sentence
        if buf and len(chunks) < max_chunks:
            chunks.append(buf)

    return chunks[:max_chunks]


def build_rag_context_from_chunks(chunks: list[str], *, max_chars: int = 10000) -> str:
    """Merge ranked chunks into a single RAG context string for the LLM."""
    if not chunks:
        return ""
    parts: list[str] = []
    total = 0
    for idx, chunk in enumerate(chunks, start=1):
        block = f"[Chunk {idx}]\n{chunk.strip()}"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block) + 2
    return "\n\n---\n\n".join(parts)


def prepare_topic_context(
    raw_rag: str,
    *,
    topic: str,
    max_chars: int = 10000,
) -> dict[str, Any]:
    """Full clean → chunk → merge stage used by the exam notes pipeline."""
    cleaned = clean_study_text(raw_rag)
    chunks = semantic_chunks(cleaned, topic=topic)
    context = build_rag_context_from_chunks(chunks, max_chars=max_chars)
    return {
        "cleaned_text": cleaned,
        "chunks": chunks,
        "rag_context": context,
        "chunk_count": len(chunks),
    }
