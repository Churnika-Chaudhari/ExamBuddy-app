"""
Stage 1 — Analyze uploaded PYQs and extract important engineering topics.

Purpose:
  Identify recurring syllabus topics from question paper text.

Inputs:
  - Cleaned PYQ text + subject hint + document count

Outputs:
  - { subject, topics: [{name, frequency}] } — JSON only, no notes

Isolation rules:
  - Never generates study notes or explanations.
  - Local extraction first; AI only when local yields no topics.

Failure modes:
  - Empty PYQ → empty topic list
  - AI unavailable → local-only extraction
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.pipeline.text_preprocessor import preprocess_pyq_text
from app.services.pipeline.three_stage.models import Stage1Result, TopicItem, topics_from_dicts
from app.services.pipeline.topic_pipeline import extract_and_merge_topics
from app.utils.text_sanitizer import sanitize_topic_name
from app.utils.text_sanitizer import sanitize_topic_name

logger = logging.getLogger("exambuddy.pipeline.stage1")

STAGE1_SYSTEM_PROMPT = """You are ExamBuddy Stage 1 — PYQ topic extractor for engineering exams.

Task: Read previous-year question paper text and extract IMPORTANT syllabus topics only.

Rules:
- Return ONLY valid JSON matching the schema
- Do NOT generate study notes
- Do NOT invent topics that are not supported by the questions
- Group similar questions under one topic name
- frequency = how often the topic (or close variants) appears
- Prefer clear engineering syllabus topic names

JSON schema:
{
  "subject": "Subject name or General",
  "topics": [
    {"name": "Topic Name", "frequency": 3}
  ]
}
"""

STAGE1_USER_PROMPT = """Extract important engineering topics from these PYQs.

Subject hint: {subject}
Number of papers: {num_documents}

PYQ text:
{pyq_text}

Return JSON only. No notes.
"""


def _filter_valid_topics(topics: list[TopicItem]) -> list[TopicItem]:
    """Drop OCR/encoding garbage before topics reach Stage 2 / notes."""
    out: list[TopicItem] = []
    for item in topics:
        name = sanitize_topic_name(item.name)
        if not name:
            continue
        out.append(TopicItem(name=name, frequency=item.frequency))
    return out


def _from_local_analysis(
    local: dict[str, Any],
    *,
    subject: str,
) -> list[TopicItem]:
    topics: list[TopicItem] = []
    table = local.get("topic_frequency_table") or local.get("academic_topic_table") or []
    if table:
        topics = topics_from_dicts(
            [
                {
                    "name": row.get("topic") or row.get("name"),
                    "frequency": row.get("frequency") or row.get("count") or 1,
                }
                for row in table
                if isinstance(row, dict)
            ]
        )
    if not topics and local.get("topic_frequency"):
        freq_map = local.get("topic_frequency") or {}
        if isinstance(freq_map, dict):
            topics = [
                TopicItem(name=str(name), frequency=int(freq or 1))
                for name, freq in freq_map.items()
                if str(name).strip()
            ]
            topics.sort(key=lambda t: (-t.frequency, t.name.lower()))
    return _filter_valid_topics(topics)


def _filter_valid_topics(topics: list[TopicItem]) -> list[TopicItem]:
    """Drop OCR/encoding garbage so corrupted names never reach Gemini."""
    out: list[TopicItem] = []
    for item in topics:
        name = sanitize_topic_name(item.name)
        if not name:
            continue
        out.append(TopicItem(name=name, frequency=item.frequency))
    return out


def extract_topics_local(
    pyq_text: str,
    *,
    subject: str | None = None,
    num_documents: int = 1,
) -> Stage1Result:
    """Stage 1 local path: preprocess → extract topics → structured result."""
    subject_label = (subject or "General").strip() or "General"
    logger.info("Stage1 local extract start subject=%s chars=%d", subject_label, len(pyq_text or ""))
    preprocessed = preprocess_pyq_text(pyq_text or "")
    local = extract_and_merge_topics(
        preprocessed.question_lines,
        num_documents=num_documents,
    )
    topics = _filter_valid_topics(_from_local_analysis(local, subject=subject_label))
    logger.info(
        "Stage1 local extract done topics=%d questions=%d sample=%s",
        len(topics),
        len(preprocessed.question_lines),
        [t.name for t in topics[:8]],
    )
    return Stage1Result(
        subject=subject_label,
        topics=topics,
        metadata={
            "stage": 1,
            "provider": "local",
            "questions_parsed": len(preprocessed.question_lines),
            "lines_removed": getattr(preprocessed.stats, "lines_removed", None),
            "cleaned_chars": len(preprocessed.cleaned_text or ""),
        },
    )


async def extract_topics_with_ai(
    pyq_text: str,
    *,
    subject: str | None = None,
    num_documents: int = 1,
    generate_json,
    max_chars: int = 14000,
) -> Stage1Result | None:
    """
    Optional Stage 1 AI path — topic extraction JSON only.

    generate_json: async (system, user) -> (dict, metadata)
    """
    text = (pyq_text or "").strip()
    if not text or generate_json is None:
        return None
    subject_label = (subject or "General").strip() or "General"
    clipped = text if len(text) <= max_chars else text[:max_chars]
    user = STAGE1_USER_PROMPT.format(
        subject=subject_label,
        num_documents=max(1, num_documents),
        pyq_text=clipped,
    )
    try:
        raw, meta = await generate_json(STAGE1_SYSTEM_PROMPT, user)
    except Exception as exc:
        logger.warning("Stage 1 AI extraction failed: %s", exc)
        return None

    if not isinstance(raw, dict):
        return None
    topics = _filter_valid_topics(topics_from_dicts(raw.get("topics")))
    if not topics:
        return None
    logger.info("Stage 1 AI extracted topics=%d", len(topics))
    return Stage1Result(
        subject=str(raw.get("subject") or subject_label).strip() or subject_label,
        topics=topics,
        metadata={
            "stage": 1,
            "provider": (meta or {}).get("provider", "ai"),
            "model": (meta or {}).get("model"),
            **{k: v for k, v in (meta or {}).items() if k in ("tokens_used", "prompt_version")},
        },
    )


async def run_stage1(
    pyq_text: str,
    *,
    subject: str | None = None,
    num_documents: int = 1,
    generate_json=None,
) -> Stage1Result:
    """
    Run Stage 1: local extraction first; AI only if local is empty and AI is available.
    Never generates notes.
    """
    local = extract_topics_local(
        pyq_text,
        subject=subject,
        num_documents=num_documents,
    )
    if local.topics:
        logger.info("Stage 1 local topics=%d subject=%s", len(local.topics), local.subject)
        return local

    if generate_json is not None:
        ai_result = await extract_topics_with_ai(
            pyq_text,
            subject=subject,
            num_documents=num_documents,
            generate_json=generate_json,
        )
        if ai_result and ai_result.topics:
            logger.info("Stage 1 AI topics=%d subject=%s", len(ai_result.topics), ai_result.subject)
            return ai_result

    return local
