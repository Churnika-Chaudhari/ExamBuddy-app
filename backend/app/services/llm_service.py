"""
Centralized LLM orchestration — context trimming, call minimization, streaming.

Performance goals:
- Pass only small, topic-relevant snippets to the model
- Skip redundant PYQ analysis LLM calls when local pipeline is sufficient
- Single structured JSON call per topic for notes (no nested queries)
- Optional token streaming for progressive UI updates
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.core.config import get_settings, reload_settings
from app.core.exceptions import ExternalServiceError
from app.services.ai.base_provider import (
    GEMINI_MAX_NOTES_TOKENS,
    BaseAIProvider,
    GeminiProvider,
    OpenAIProvider,
)
from app.services.ai.provider_order import resolve_provider_order
from app.services.ai.prompts import (
    PROMPT_VERSION,
    PYQ_ANALYSIS_SYSTEM_PROMPT,
    PYQ_ANALYSIS_USER_PROMPT,
)
from app.services.notes_engine.prompt_builder import build_exam_notes_prompts


logger = logging.getLogger(__name__)

# Tight context windows — large prompts are the main latency driver.
MAX_RAG_CONTEXT_CHARS = 12_000
MAX_ANALYSIS_CONTEXT_CHARS = 2_000
MAX_PIPELINE_CONTEXT_CHARS = 1_200
MAX_PYQ_QUESTIONS_CHARS = 4_000
MAX_PYQ_CONTENT_CHARS = 12_000
MIN_LOCAL_TOPICS_FOR_SKIP = 2

# Notes generation sampling — factual, structured, low hallucination.
NOTES_TEMPERATURE = 0.35
NOTES_TOP_P = 0.9


def trim_context(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit("\n", 1)[0].strip() + "\n…"


def compact_analysis_context(analysis: dict[str, Any]) -> str:
    """Compact PYQ signals for notes — related topics only, no motivational labels."""
    if not analysis:
        return ""
    parts: list[str] = []
    summary = (analysis.get("summary") or "").strip()
    if summary:
        parts.append(summary[:400])

    for row in (analysis.get("topic_frequency_table") or [])[:12]:
        topic = row.get("topic")
        if topic:
            parts.append(f"- Related syllabus topic: {topic}")

    return trim_context("\n".join(parts), MAX_ANALYSIS_CONTEXT_CHARS)


def extract_pyq_questions_for_topic(analysis: dict[str, Any] | None, topic: str) -> str:
    """Pull PYQ question snippets related to the topic for notes grounding."""
    if not analysis or not topic:
        return ""
    topic_l = topic.strip().lower()
    tokens = [t for t in topic_l.replace("-", " ").split() if len(t) > 2]
    collected: list[str] = []

    def _maybe_add(text: str) -> None:
        cleaned = " ".join(text.split()).strip()
        if not cleaned or len(cleaned) < 12:
            return
        lower = cleaned.lower()
        if topic_l in lower or any(tok in lower for tok in tokens):
            if cleaned not in collected:
                collected.append(cleaned)

    for item in analysis.get("repeated_questions") or []:
        if isinstance(item, str):
            _maybe_add(item)
        elif isinstance(item, dict):
            _maybe_add(str(item.get("question") or item.get("text") or item.get("q") or ""))

    for key in ("important_questions", "sample_questions", "questions"):
        for item in analysis.get(key) or []:
            if isinstance(item, str):
                _maybe_add(item)
            elif isinstance(item, dict):
                _maybe_add(str(item.get("question") or item.get("text") or ""))

    # Fallback: pull question-like lines from analysis summary / raw excerpts.
    for blob_key in ("question_bank", "extracted_questions", "content_excerpt"):
        blob = analysis.get(blob_key)
        if isinstance(blob, str):
            for line in blob.splitlines():
                if "?" in line or line.strip().lower().startswith(("explain", "define", "describe", "write", "compare", "differentiate")):
                    _maybe_add(line)

    if not collected:
        return (
            f"No direct PYQ question text matched for '{topic}'. "
            "Generate complete syllabus notes suitable for typical university exam questions "
            "(define / explain / compare / short notes)."
        )

    lines = [f"- {q}" for q in collected[:12]]
    return trim_context("\n".join(lines), MAX_PYQ_QUESTIONS_CHARS)


def should_skip_pyq_llm(local_topics: dict[str, Any] | None) -> bool:
    """
    Local pipeline already extracted syllabus topics — skip a slow validation LLM call.
    Saves 5–20s per analysis on typical PYQ papers.
    """
    if not local_topics:
        return False
    table = local_topics.get("topic_table") or []
    syllabus = local_topics.get("syllabus_topics") or []
    return len(table) >= MIN_LOCAL_TOPICS_FOR_SKIP or len(syllabus) >= MIN_LOCAL_TOPICS_FOR_SKIP


class LLMService:
    def __init__(self) -> None:
        self.settings = reload_settings()
        self.providers: list[tuple[str, BaseAIProvider]] = []
        self._load_providers()
        self.ai_available = bool(self.providers)

    def _build_provider(self, provider_name: str) -> BaseAIProvider:
        if provider_name == "gemini":
            if not self.settings.gemini_api_key:
                raise ExternalServiceError("Gemini API key is not configured")
            return GeminiProvider(self.settings.gemini_api_key, self.settings.gemini_model)
        if not self.settings.openai_api_key:
            raise ExternalServiceError("OpenAI API key is not configured")
        return OpenAIProvider(self.settings.openai_api_key, self.settings.openai_model)

    def _load_providers(self) -> None:
        for name in resolve_provider_order(self.settings):
            try:
                self.providers.append((name, self._build_provider(name)))
            except ExternalServiceError as exc:
                logger.warning("LLM provider %s unavailable: %s", name, exc.message)
        if self.providers:
            logger.info("LLM providers ready: %s", [name for name, _ in self.providers])

    async def _generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.providers:
            raise ExternalServiceError("Configure OpenAI or Gemini API key in backend .env")

        last_exc: Exception | None = None
        for name, provider in self.providers:
            try:
                result, metadata = await provider.generate_json(
                    system_prompt,
                    user_prompt,
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                metadata["prompt_version"] = PROMPT_VERSION
                return result, metadata
            except Exception as exc:
                logger.error("%s JSON generation failed: %s", name, exc)
                last_exc = exc
        raise ExternalServiceError("AI generation failed for all configured providers") from last_exc

    def build_topic_notes_prompts(
        self,
        topic: str,
        *,
        rag_context: str = "",
        analysis_context: str = "",
        subject: str | None = None,
        pipeline_context: str = "",
        exam_priority: str = "",
        pyq_questions: str = "",
    ) -> tuple[str, str]:
        return build_exam_notes_prompts(
            topic=topic,
            subject=subject or "General",
            rag_context=trim_context(rag_context, MAX_RAG_CONTEXT_CHARS),
            analysis_context=trim_context(analysis_context, MAX_ANALYSIS_CONTEXT_CHARS)
            or "No additional analysis signals.",
            pipeline_context=trim_context(pipeline_context, MAX_PIPELINE_CONTEXT_CHARS),
            exam_priority=exam_priority.strip() or "Standard syllabus priority",
            pyq_questions=trim_context(pyq_questions, MAX_PYQ_QUESTIONS_CHARS)
            or (
                f"No direct PYQ text for '{topic}'. "
                "Cover definition, key concepts, comparison, common mistakes, and typical 5/10-mark angles."
            ),
        )

    async def generate_topic_notes_json(
        self,
        topic: str,
        *,
        rag_context: str = "",
        analysis_context: str = "",
        subject: str | None = None,
        pipeline_context: str = "",
        exam_priority: str = "",
        pyq_questions: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Single structured LLM call for topic notes."""
        system_prompt, user_prompt = self.build_topic_notes_prompts(
            topic,
            rag_context=rag_context,
            analysis_context=analysis_context,
            subject=subject,
            pipeline_context=pipeline_context,
            exam_priority=exam_priority,
            pyq_questions=pyq_questions,
        )
        return await self._generate_json(
            system_prompt,
            user_prompt,
            max_output_tokens=GEMINI_MAX_NOTES_TOKENS,
            temperature=NOTES_TEMPERATURE,
            top_p=NOTES_TOP_P,
        )

    async def stream_topic_notes_tokens(
        self,
        topic: str,
        *,
        rag_context: str = "",
        analysis_context: str = "",
        subject: str | None = None,
        pipeline_context: str = "",
        exam_priority: str = "",
        pyq_questions: str = "",
    ) -> AsyncIterator[str]:
        """
        Stream raw model tokens for progressive UI rendering.
        Yields text fragments as they arrive from the provider.
        """
        if not self.providers:
            raise ExternalServiceError("Configure OpenAI or Gemini API key in backend .env")

        system_prompt, user_prompt = self.build_topic_notes_prompts(
            topic,
            rag_context=rag_context,
            analysis_context=analysis_context,
            subject=subject,
            pipeline_context=pipeline_context,
            exam_priority=exam_priority,
            pyq_questions=pyq_questions,
        )

        last_exc: Exception | None = None
        for name, provider in self.providers:
            stream_fn = getattr(provider, "stream_text", None)
            if not callable(stream_fn):
                continue
            try:
                async for token in stream_fn(
                    system_prompt,
                    user_prompt,
                    max_output_tokens=GEMINI_MAX_NOTES_TOKENS,
                    temperature=NOTES_TEMPERATURE,
                    top_p=NOTES_TOP_P,
                ):
                    if token:
                        yield token
                return
            except Exception as exc:
                logger.warning("%s stream failed: %s", name, exc)
                last_exc = exc

        raise ExternalServiceError("Streaming not available") from last_exc

    async def analyze_pyq_with_llm(
        self,
        content: str,
        subject: str | None,
        *,
        num_documents: int,
        extracted_topics_hint: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_prompt = PYQ_ANALYSIS_USER_PROMPT.format(
            subject=subject or "General",
            num_documents=num_documents,
            content=trim_context(content, MAX_PYQ_CONTENT_CHARS),
            extracted_topics=extracted_topics_hint or "None pre-extracted",
        )
        return await self._generate_json(PYQ_ANALYSIS_SYSTEM_PROMPT, user_prompt)
