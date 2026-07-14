"""
Orchestrates PYQ → clean → topics → Gemini notes workflow.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from app.services.pipeline.text_preprocessor import PreprocessResult, preprocess_pyq_text
from app.services.pipeline.topic_pipeline import extract_and_merge_topics
from app.utils.topic_extractor import sanitize_analysis_result

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    cleaned_text: str
    question_lines: list[str]
    topic_analysis: dict[str, Any]
    preprocess_stats: Any


class NotesPipeline:
    """Unified notes generation preprocessing pipeline."""

    def preprocess(self, raw_text: str) -> PreprocessResult:
        return preprocess_pyq_text(raw_text)

    def extract_topics(
        self,
        cleaned_text: str,
        question_lines: list[str] | None = None,
        *,
        subject: str | None = None,
        num_documents: int = 1,
        preprocessed: PreprocessResult | None = None,
    ) -> dict[str, Any]:
        lines = question_lines or []
        result = extract_and_merge_topics(lines, num_documents=num_documents)
        if result:
            return result

        # Deferred import breaks cycle: topic_analysis → pipeline.text_preprocessor
        from app.utils.topic_analysis import build_consolidated_analysis

        return build_consolidated_analysis(
            cleaned_text,
            subject=subject,
            num_documents=num_documents,
            preprocessed=preprocessed,
        )

    def run(
        self,
        raw_text: str,
        *,
        subject: str | None = None,
        num_documents: int = 1,
        preprocessed: PreprocessResult | None = None,
    ) -> PipelineResult:
        """Single preprocess pass — reuse *preprocessed* when text was already cleaned."""
        if preprocessed is None:
            preprocessed = self.preprocess(raw_text)
        else:
            logger.debug("Reusing cached preprocess result (%d chars)", len(preprocessed.cleaned_text))

        topic_analysis = self.extract_topics(
            preprocessed.cleaned_text,
            preprocessed.question_lines,
            subject=subject,
            num_documents=num_documents,
            preprocessed=preprocessed,
        )
        return PipelineResult(
            cleaned_text=preprocessed.cleaned_text,
            question_lines=preprocessed.question_lines,
            topic_analysis=topic_analysis,
            preprocess_stats=preprocessed.stats,
        )

    async def run_async(
        self,
        raw_text: str,
        *,
        subject: str | None = None,
        num_documents: int = 1,
        preprocessed: PreprocessResult | None = None,
    ) -> PipelineResult:
        """CPU-bound pipeline in a thread pool — does not block the event loop."""
        return await asyncio.to_thread(
            self.run,
            raw_text,
            subject=subject,
            num_documents=num_documents,
            preprocessed=preprocessed,
        )

    def merge_ai_analysis(
        self,
        local: dict[str, Any],
        ai: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Prefer locally extracted canonical topics; enrich with AI summary/patterns.
        Local pipeline guarantees clean topic names without instruction verbs.
        """
        if not local.get("topic_table"):
            return sanitize_analysis_result(ai)

        merged = dict(local)
        if ai.get("exam_patterns"):
            merged["exam_patterns"] = ai["exam_patterns"]
        if ai.get("summary") and "Analyzed" not in str(ai.get("summary", "")):
            merged["ai_summary"] = ai["summary"]
        return sanitize_analysis_result(merged)

    @staticmethod
    def topic_frequency_label(frequency: int | None) -> str:
        if frequency is None:
            return ""
        if frequency >= 3:
            return "⭐ Frequently Asked in Exams"
        if frequency == 2:
            return "Often Asked in Exams"
        return ""

    def build_notes_context(
        self,
        topic: str,
        analysis: dict[str, Any] | None,
        *,
        frequency: int | None = None,
    ) -> str:
        """Extra context injected into Gemini notes prompt."""
        parts: list[str] = []
        if analysis:
            summary = (analysis.get("summary") or "").strip()
            if summary:
                parts.append(summary[:400])
            freq_table = analysis.get("topic_frequency_table") or []
            for row in freq_table:
                if str(row.get("topic", "")).lower() == topic.lower():
                    frequency = frequency or int(row.get("frequency", 0))
                    break

        label = self.topic_frequency_label(frequency)
        if label:
            parts.append(f"Exam priority for this topic: {label}")
        parts.append(
            "Write clean textbook-quality notes. Never include file names, subject codes, "
            "upload labels, or question-paper metadata in the output."
        )
        return "\n".join(p for p in parts if p).strip()
