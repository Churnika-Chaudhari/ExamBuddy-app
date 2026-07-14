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
from app.services.ai.prompts import (
    PROMPT_VERSION,
    PYQ_ANALYSIS_SYSTEM_PROMPT,
    PYQ_ANALYSIS_USER_PROMPT,
    TOPIC_NOTES_SYSTEM_PROMPT,
    TOPIC_NOTES_USER_PROMPT,
)

logger = logging.getLogger(__name__)

# Tight context windows — large prompts are the main latency driver.
MAX_RAG_CONTEXT_CHARS = 10_000
MAX_ANALYSIS_CONTEXT_CHARS = 1_500
MAX_PIPELINE_CONTEXT_CHARS = 800
MAX_PYQ_CONTENT_CHARS = 12_000
MIN_LOCAL_TOPICS_FOR_SKIP = 2


def trim_context(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit("\n", 1)[0].strip() + "\n…"


def compact_analysis_context(analysis: dict[str, Any]) -> str:
    """Small PYQ summary for notes prompt — topic names + frequency only."""
    if not analysis:
        return ""
    parts: list[str] = []
    summary = (analysis.get("summary") or "").strip()
    if summary:
        parts.append(summary[:400])

    for row in (analysis.get("topic_frequency_table") or [])[:10]:
        topic = row.get("topic")
        freq = row.get("frequency")
        if topic:
            parts.append(f"- {topic} (asked {freq}x)" if freq else f"- {topic}")

    for item in (analysis.get("high_priority_topics") or [])[:5]:
        if isinstance(item, str):
            parts.append(f"- Priority: {item}")
        elif isinstance(item, dict) and item.get("topic"):
            parts.append(f"- Priority: {item['topic']}")

    return trim_context("\n".join(parts), MAX_ANALYSIS_CONTEXT_CHARS)


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
        preferred = self.settings.ai_provider
        order = [preferred, "gemini" if preferred == "openai" else "openai"]
        seen: set[str] = set()
        for name in order:
            if name in seen:
                continue
            seen.add(name)
            try:
                self.providers.append((name, self._build_provider(name)))
            except ExternalServiceError as exc:
                logger.warning("LLM provider %s unavailable: %s", name, exc.message)

    async def _generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_output_tokens: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.providers:
            raise ExternalServiceError("Configure OpenAI or Gemini API key in backend .env")

        last_exc: Exception | None = None
        for name, provider in self.providers:
            try:
                result, metadata = await provider.generate_json(
                    system_prompt, user_prompt, max_output_tokens=max_output_tokens
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
    ) -> tuple[str, str]:
        user_prompt = TOPIC_NOTES_USER_PROMPT.format(
            topic=topic,
            subject=subject or "General",
            exam_priority=exam_priority or "",
            rag_context=trim_context(rag_context, MAX_RAG_CONTEXT_CHARS)
            or "No reference snippets available — use standard syllabus knowledge.",
            analysis_context=trim_context(analysis_context, MAX_ANALYSIS_CONTEXT_CHARS)
            or "No PYQ emphasis data.",
            pipeline_context=trim_context(pipeline_context, MAX_PIPELINE_CONTEXT_CHARS),
        )
        return TOPIC_NOTES_SYSTEM_PROMPT, user_prompt

    async def generate_topic_notes_json(
        self,
        topic: str,
        *,
        rag_context: str = "",
        analysis_context: str = "",
        subject: str | None = None,
        pipeline_context: str = "",
        exam_priority: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Single structured LLM call for topic notes."""
        system_prompt, user_prompt = self.build_topic_notes_prompts(
            topic,
            rag_context=rag_context,
            analysis_context=analysis_context,
            subject=subject,
            pipeline_context=pipeline_context,
            exam_priority=exam_priority,
        )
        return await self._generate_json(
            system_prompt,
            user_prompt,
            max_output_tokens=GEMINI_MAX_NOTES_TOKENS,
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
