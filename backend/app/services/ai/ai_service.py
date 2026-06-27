import logging
import re
from typing import Any

from app.core.config import get_settings, reload_settings
from app.core.exceptions import ExternalServiceError
from app.services.ai.base_provider import (
    GEMINI_MAX_NOTES_TOKENS,
    BaseAIProvider,
    GeminiProvider,
    OpenAIProvider,
)
from app.services.ai.local_analyzer import analyze_pyq_local
from app.utils.topic_extractor import sanitize_analysis_result
from app.services.ai.prompts import (
    NOTES_GENERATE_SYSTEM_PROMPT,
    NOTES_GENERATE_USER_PROMPT,
    NOTES_SIMPLIFY_SYSTEM_PROMPT,
    NOTES_SIMPLIFY_USER_PROMPT,
    PROMPT_VERSION,
    PYQ_ANALYSIS_SYSTEM_PROMPT,
    PYQ_ANALYSIS_USER_PROMPT,
    QUIZ_GENERATE_SYSTEM_PROMPT,
    QUIZ_GENERATE_USER_PROMPT,
    TOPIC_NOTES_SYSTEM_PROMPT,
    TOPIC_NOTES_USER_PROMPT,
)

logger = logging.getLogger(__name__)


# Control + zero-width characters that should never appear in rendered notes.
_CONTROL_CHARS = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u200b-\u200d\ufeff]")
# Lines that are pure ASCII-diagram / box-drawing / arrow noise.
_DIAGRAM_LINE = re.compile(r"^[\s|+_\-=*/\\<>^v.~`#─━│┌┐└┘├┤┬┴┼╔╗╚╝→←↑↓⇒⇐•]+$")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:|\-]+\|[\s:|\-]*$")
# Decorative symbols that look like junk in plain notes.
_ARROWS_RIGHT = re.compile(r"[→⇒⟶➡]")
_ARROWS_LEFT = re.compile(r"[←⇐⟵]")
_BOX_CHARS = re.compile(r"[─━│┌┐└┘├┤┬┴┼╔╗╚╝█▀▄▌▐░▒▓↑↓↕↔]")


def clean_notes_markdown(text: str) -> str:
    """
    Strip noise from AI/markdown notes so only clean, important content remains:
    removes control/zero-width chars, markdown tables, ASCII diagrams, code
    fences, backticks and decorative symbols the simple renderer can't display.
    """
    if not text:
        return ""

    text = _CONTROL_CHARS.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))

    out: list[str] = []
    for raw in text.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()

        # Drop code-fence markers entirely (keep the inner text as plain lines).
        if stripped.startswith("```") or stripped.startswith("~~~"):
            continue

        # Markdown table separator row: | --- | :--: |
        if "-" in stripped and _TABLE_SEPARATOR.match(stripped):
            continue

        # Markdown table data row: | a | b | -> "a — b"
        if stripped.startswith("|") and stripped.count("|") >= 2:
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            cells = [c for c in cells if c]
            line = "- " + " — ".join(cells) if cells else ""
            stripped = line.strip()
            if not stripped:
                continue

        # Pure ASCII-diagram / arrow / box lines add no value -> drop.
        if len(stripped) >= 3 and _DIAGRAM_LINE.match(stripped):
            continue

        # Remove inline backticks but keep the wrapped text.
        line = re.sub(r"`+", "", line)
        # Convert decorative arrows to plain ASCII and drop box-drawing chars.
        line = _ARROWS_RIGHT.sub("->", line)
        line = _ARROWS_LEFT.sub("<-", line)
        line = _BOX_CHARS.sub("", line)
        # Remove leftover stray pipe characters.
        line = line.replace("|", " ")
        # Collapse internal runs of spaces created by the substitutions.
        line = re.sub(r"[ \t]{2,}", " ", line).rstrip()

        out.append(line)

    cleaned = "\n".join(out)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _friendly_ai_error(message: str) -> str:
    lower = message.lower()
    if "429" in message or "quota" in lower:
        return "Gemini API quota exceeded. Notes generated from local template — retry later for AI notes."
    if "401" in message or "403" in message or "api key" in lower:
        return "Invalid or missing API key. Notes generated from local template."
    if "404" in message and "model" in lower:
        return "AI model unavailable. Notes generated from local template."
    return "AI generation failed. Notes generated from local template."


class AIService:
    def __init__(self) -> None:
        self.settings = reload_settings()
        self.providers: list[tuple[str, BaseAIProvider]] = []
        self._load_providers()
        self.ai_available = bool(self.providers)
        self.provider = self.providers[0][1] if self.providers else None

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
                logger.warning("AI provider %s unavailable: %s", name, exc.message)

        if not self.providers:
            logger.warning("No AI provider configured — using local fallbacks where possible")

    async def _generate_json_with_fallback(
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

    def _local_notes_result(
        self,
        topics: list[str],
        context: str,
        subject: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        subject_label = subject or "Study"
        sections = [
            f"# {subject_label} — Topic Answers\n",
            "_Configure OPENAI_API_KEY or GEMINI_API_KEY in backend .env for AI-generated answers._\n",
        ]
        if context.strip():
            sections.append(f"## Analysis Overview\n{context[:4000]}\n")
        for topic in topics[:15]:
            sections.append(
                f"## {topic}\n"
                f"### Definition\n"
                f"Core concept tested in previous year papers.\n\n"
                f"### Key Points\n"
                f"- Important theory and definitions for **{topic}**\n"
                f"- Common exam question patterns from PYQ analysis\n"
                f"- Practice numericals / diagrams where applicable\n\n"
                f"### Exam Tips\n"
                f"- Revise standard definitions and compare with related topics\n"
            )
        content = "\n".join(sections)
        return {
            "title": f"{subject_label} — Topic Answers",
            "content": content,
            "summary": f"Study answers for {len(topics)} topics. Add an AI API key for full ChatGPT/Gemini answers.",
            "topics": topics,
        }, {"provider": "local", "model": "rule-based", "prompt_version": PROMPT_VERSION}

    async def analyze_pyq(
        self,
        content: str,
        subject: str | None = None,
        *,
        num_documents: int = 1,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not content.strip():
            raise ExternalServiceError("No text content to analyze")

        if self.ai_available:
            user_prompt = PYQ_ANALYSIS_USER_PROMPT.format(
                subject=subject or "General",
                num_documents=num_documents,
                content=content[:50000],
            )
            try:
                result, metadata = await self._generate_json_with_fallback(
                    PYQ_ANALYSIS_SYSTEM_PROMPT, user_prompt
                )
                result = sanitize_analysis_result(result)
                if not result.get("topic_table"):
                    local = analyze_pyq_local(content, subject)
                    for key in (
                        "topic_table", "academic_topic_table", "most_important_topics",
                        "frequently_asked_topics", "rarely_asked_topics", "topic_groups",
                        "syllabus_topics", "topic_frequency", "important_topics",
                    ):
                        result.setdefault(key, local.get(key, [] if key != "topic_frequency" else {}))
                return result, metadata
            except Exception as exc:
                logger.error("PYQ analysis AI failed, falling back to local: %s", exc)

        from app.utils.topic_analysis import build_consolidated_analysis

        result = build_consolidated_analysis(
            content, subject=subject, num_documents=num_documents
        )
        metadata = {
            "provider": "local",
            "model": "rule-based",
            "tokens_used": None,
            "prompt_version": PROMPT_VERSION,
        }
        return result, metadata

    def _local_topic_notes(
        self,
        topic: str,
        subject: str | None,
        *,
        rag_context: str = "",
        analysis_context: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        subject_label = subject or "Study"
        retrieved_hint = ""
        if rag_context.strip():
            retrieved_hint = "\n\n_Based on retrieved content from your uploaded documents._\n"
            excerpt = rag_context[:1500].replace("RETRIEVED CONTENT", "").strip()
            retrieved_hint += f"\n> {excerpt[:800]}...\n"

        content = f"""# {topic}

## Definition
{topic} is a core {subject_label} concept tested in university exams.

## Explanation
{topic} is an important syllabus topic. Focus on the core definitions, the main principles, and how {topic} is applied to solve problems.{retrieved_hint}

## Key Points
- Fundamental definitions and terminology of **{topic}**
- Core principles and relationships
- Standard exam question patterns from previous year papers

## Example
A practical example illustrating how {topic} is used in real scenarios.

## Advantages and Disadvantages
- Benefits of {topic} in academic and real-world contexts
- Limitations and trade-offs to keep in mind

## Important Exam Questions
- What is {topic}? Give a clear definition with its purpose.
- Why is {topic} important and where is it applied?
- Compare {topic} with related topics from the syllabus.

## Quick Revision
- One-line definition
- Three key points
- One example
- One exam tip

Add OPENAI_API_KEY or GEMINI_API_KEY in backend .env for full AI and RAG notes."""
        meta: dict[str, Any] = {
            "provider": "local",
            "model": "rule-based",
            "prompt_version": PROMPT_VERSION,
            "rag_chunk_count": 1 if rag_context.strip() else 0,
        }
        return {
            "notes": content,
            "summary": f"Structured notes for {topic}. Configure AI keys for RAG-enhanced generation.",
        }, meta

    def _normalize_topic_result(self, result: dict[str, Any]) -> dict[str, Any]:
        notes = (
            result.get("notes")
            or result.get("content")
            or result.get("markdown")
            or ""
        )
        if isinstance(notes, dict):
            notes = str(notes)
        notes = clean_notes_markdown(str(notes))
        summary = clean_notes_markdown(str(result.get("summary") or "")).strip()
        return {"notes": notes, "summary": summary or None}

    async def generate_topic_notes(
        self,
        topic: str,
        *,
        rag_context: str = "",
        analysis_context: str = "",
        subject: str | None = None,
        rag_sources: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.ai_available:
            result, meta = self._local_topic_notes(
                topic, subject, rag_context=rag_context, analysis_context=analysis_context
            )
            if rag_sources:
                meta["rag_sources"] = rag_sources[:8]
            return result, meta

        user_prompt = TOPIC_NOTES_USER_PROMPT.format(
            topic=topic,
            subject=subject or "General",
            rag_context=rag_context[:28000] or "No retrieved document content available.",
            analysis_context=analysis_context[:8000] or "No PYQ analysis context.",
        )
        try:
            result, metadata = await self._generate_json_with_fallback(
                TOPIC_NOTES_SYSTEM_PROMPT,
                user_prompt,
                max_output_tokens=GEMINI_MAX_NOTES_TOKENS,
            )
            result = self._normalize_topic_result(result)
            if rag_sources:
                metadata["rag_sources"] = rag_sources[:8]
                metadata["rag_chunk_count"] = len(rag_sources)
            metadata["generation_mode"] = "rag" if rag_context.strip() else "ai_only"
            if not result.get("notes"):
                raise ExternalServiceError("AI returned empty notes content")
            return result, metadata
        except Exception as exc:
            logger.error("Topic notes generation failed: %s", exc)
            result, meta = self._local_topic_notes(
                topic, subject, rag_context=rag_context, analysis_context=analysis_context
            )
            meta["generation_error"] = _friendly_ai_error(str(exc))
            meta["ai_error"] = str(exc)
            if rag_sources:
                meta["rag_sources"] = rag_sources[:8]
            return result, meta

    async def generate_notes(
        self,
        topics: list[str],
        context: str,
        subject: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.ai_available:
            return self._local_notes_result(topics, context, subject)

        user_prompt = NOTES_GENERATE_USER_PROMPT.format(
            topics=", ".join(topics),
            subject=subject or "General",
            context=context[:30000] or "No prior analysis context.",
        )
        try:
            return await self._generate_json_with_fallback(
                NOTES_GENERATE_SYSTEM_PROMPT,
                user_prompt,
                max_output_tokens=GEMINI_MAX_NOTES_TOKENS,
            )
        except Exception as exc:
            logger.error("Notes generation failed, using local template: %s", exc)
            return self._local_notes_result(topics, context, subject)

    async def simplify_notes(self, title: str, content: str) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.ai_available:
            return {
                "title": f"Simplified - {title}",
                "content": content[:8000],
                "summary": content[:500],
                "topics": [],
            }, {"provider": "local", "model": "rule-based", "prompt_version": PROMPT_VERSION}

        user_prompt = NOTES_SIMPLIFY_USER_PROMPT.format(title=title, content=content[:30000])
        try:
            return await self._generate_json_with_fallback(
                NOTES_SIMPLIFY_SYSTEM_PROMPT, user_prompt
            )
        except Exception as exc:
            logger.error("Notes simplification failed: %s", exc)
            raise ExternalServiceError("Notes simplification failed") from exc

    def _local_quiz_result(
        self,
        topics: list[str],
        *,
        quiz_type: str,
        num_questions: int,
        difficulty: str,
        subject: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        import uuid

        label = subject or "Study"
        questions: list[dict[str, Any]] = []
        pool = topics[:15] or ["General Topics"]

        for i in range(min(num_questions, len(pool) * 2)):
            topic = pool[i % len(pool)]
            q_type = quiz_type
            if quiz_type == "mixed":
                q_type = ["mcq", "true_false", "fill_blank", "short_answer"][i % 4]

            if q_type == "true_false":
                questions.append(
                    {
                        "id": str(uuid.uuid4()),
                        "question_text": f"True or False: {topic} is an important exam topic in {label}.",
                        "question_type": "true_false",
                        "options": ["True", "False"],
                        "correct_answer": "True",
                        "explanation": f"{topic} appears in previous year papers for {label}.",
                        "topic": topic,
                    }
                )
            elif q_type == "fill_blank":
                questions.append(
                    {
                        "id": str(uuid.uuid4()),
                        "question_text": f"_____ is a key concept in {topic} ({label}).",
                        "question_type": "fill_blank",
                        "options": [],
                        "correct_answer": topic.split()[0] if topic else "concept",
                        "explanation": f"Review {topic} definitions.",
                        "topic": topic,
                    }
                )
            elif q_type == "short_answer":
                questions.append(
                    {
                        "id": str(uuid.uuid4()),
                        "question_text": f"Explain {topic} in 2-3 sentences.",
                        "question_type": "short_answer",
                        "options": [],
                        "correct_answer": f"Core definition and application of {topic}",
                        "explanation": f"Refer to study notes for {topic}.",
                        "topic": topic,
                    }
                )
            else:
                questions.append(
                    {
                        "id": str(uuid.uuid4()),
                        "question_text": f"Which best describes {topic}?",
                        "question_type": "mcq",
                        "options": [
                            f"Core {label} concept tested in exams",
                            "Unrelated general knowledge",
                            "Only a programming syntax rule",
                            "Not part of syllabus",
                        ],
                        "correct_answer": f"Core {label} concept tested in exams",
                        "explanation": f"{topic} is a repeated PYQ topic.",
                        "topic": topic,
                    }
                )

        return {
            "title": f"{label} — {difficulty.title()} Quiz",
            "questions": questions[:num_questions],
        }, {
            "provider": "local",
            "model": "rule-based",
            "prompt_version": PROMPT_VERSION,
            "difficulty": difficulty,
        }

    async def generate_quiz(
        self,
        content: str,
        topics: list[str],
        quiz_type: str,
        num_questions: int,
        *,
        difficulty: str = "medium",
        subject: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.ai_available:
            return self._local_quiz_result(
                topics,
                quiz_type=quiz_type,
                num_questions=num_questions,
                difficulty=difficulty,
                subject=subject,
            )

        user_prompt = QUIZ_GENERATE_USER_PROMPT.format(
            num_questions=num_questions,
            quiz_type=quiz_type,
            difficulty=difficulty,
            subject=subject or "General",
            topics=", ".join(topics) if topics else "General",
            content=content[:30000] or "No additional content.",
        )
        try:
            result, metadata = await self._generate_json_with_fallback(
                QUIZ_GENERATE_SYSTEM_PROMPT, user_prompt
            )
            metadata["difficulty"] = difficulty
            return result, metadata
        except Exception as exc:
            logger.error("Quiz generation failed, using local template: %s", exc)
            result, meta = self._local_quiz_result(
                topics,
                quiz_type=quiz_type,
                num_questions=num_questions,
                difficulty=difficulty,
                subject=subject,
            )
            meta["generation_error"] = str(exc)
            return result, meta
