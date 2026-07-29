"""
Centralized LLM orchestration — context trimming, call minimization.

Performance goals:
- Pass only small, topic-relevant snippets to the model
- Skip redundant PYQ analysis LLM calls when local pipeline is sufficient
- Small, focused structured-JSON calls per notes section batch (never one
  mega-call per topic) — see app.services.notes_engine for the sectioned
  Stage-3 notes pipeline that drives this.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings, reload_settings
from app.core.exceptions import ExternalServiceError
from app.services.ai.base_provider import BaseAIProvider, GeminiProvider, OpenAIProvider
from app.services.ai.provider_order import resolve_provider_order
from app.services.ai.prompts import (
    PROMPT_VERSION,
    PYQ_ANALYSIS_SYSTEM_PROMPT,
    PYQ_ANALYSIS_USER_PROMPT,
)


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
        response_schema: dict[str, Any] | None = None,
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
                    response_schema=response_schema,
                )
                metadata["prompt_version"] = PROMPT_VERSION
                if response_schema is not None:
                    metadata["structured_json_mode"] = True
                return result, metadata
            except Exception as exc:
                logger.error("%s JSON generation failed: %s", name, exc)
                last_exc = exc
        raise ExternalServiceError("AI generation failed for all configured providers") from last_exc

    async def generate_notes_section_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        response_schema: dict[str, Any],
        max_output_tokens: int,
        temperature: float = NOTES_TEMPERATURE,
        top_p: float = NOTES_TOP_P,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        One focused structured-JSON call for a SINGLE Stage-3 notes section batch.

        The sectioned engine (app.services.notes_engine) issues ~11 of these per
        topic — small compact schemas, never one mega-call — then merges the
        results into one long-form markdown chapter.
        """
        return await self._generate_json(
            system_prompt,
            user_prompt,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            top_p=top_p,
            response_schema=response_schema,
        )

    async def analyze_pyq_with_llm(
        self,
        content: str,
        subject: str | None,
        *,
        num_documents: int,
        extracted_topics_hint: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        LEGACY: Single-prompt PYQ analysis.

        Production path uses Stage 1+2 via run_topic_pipeline in AnalysisService.
        """
        user_prompt = PYQ_ANALYSIS_USER_PROMPT.format(
            subject=subject or "General",
            num_documents=num_documents,
            content=trim_context(content, MAX_PYQ_CONTENT_CHARS),
            extracted_topics=extracted_topics_hint or "None pre-extracted",
        )
        return await self._generate_json(PYQ_ANALYSIS_SYSTEM_PROMPT, user_prompt)
