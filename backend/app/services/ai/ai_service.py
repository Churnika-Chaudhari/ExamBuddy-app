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
from app.services.ai.provider_order import resolve_provider_order
from app.services.ai.local_analyzer import analyze_pyq_local
from app.services.ai.notes_sanitizer import is_placeholder_notes, sanitize_note_text
from app.services.llm_service import LLMService, should_skip_pyq_llm
from app.utils.topic_extractor import sanitize_analysis_result
from app.services.ai.notes_structured import (
    extract_structured_payload,
    is_structured_notes_result,
    structured_notes_to_markdown,
)
from app.services.notes_engine.pipeline import ExamNotesPipeline
from app.services.notes_engine.markdown_formatter import format_exam_notes_markdown
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


# Motivational filler detection lives in notes_sanitizer.is_placeholder_notes.


def clean_notes_markdown(text: str) -> str:
    """
    Clean AI/markdown notes for display:
    removes control/zero-width chars and document noise, while preserving
    headings, bullets, code fences, tables, and useful diagram lines.
    """
    if not text:
        return ""

    text = _CONTROL_CHARS.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))

    out: list[str] = []
    in_code = False
    for raw in text.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code = not in_code
            out.append(stripped[:3])
            continue

        if in_code:
            out.append(line)
            continue

        if not stripped:
            out.append("")
            continue

        # Keep markdown tables intact for the renderer / PDF export.
        if stripped.startswith("|") or (_TABLE_SEPARATOR.match(stripped) and "-" in stripped):
            out.append(line)
            continue

        # Keep ASCII diagram / flow lines (monospace-friendly).
        if len(stripped) >= 3 and _DIAGRAM_LINE.match(stripped):
            out.append(line)
            continue

        # Soft-normalize decorative arrows; keep readable content.
        line = _ARROWS_RIGHT.sub("->", line)
        line = _ARROWS_LEFT.sub("<-", line)
        line = re.sub(r"[ \t]{2,}", " ", line).rstrip()
        out.append(line)

    cleaned = "\n".join(out)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return sanitize_note_text(cleaned.strip())


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
        self.llm_service = LLMService()

    def _build_provider(self, provider_name: str) -> BaseAIProvider:
        if provider_name == "gemini":
            if not self.settings.gemini_api_key:
                raise ExternalServiceError("Gemini API key is not configured")
            return GeminiProvider(self.settings.gemini_api_key, self.settings.gemini_model)
        if not self.settings.openai_api_key:
            raise ExternalServiceError("OpenAI API key is not configured")
        return OpenAIProvider(self.settings.openai_api_key, self.settings.openai_model)

    def _load_providers(self) -> None:
        order = resolve_provider_order(self.settings)
        for name in order:
            try:
                self.providers.append((name, self._build_provider(name)))
            except ExternalServiceError as exc:
                logger.warning("AI provider %s unavailable: %s", name, exc.message)

        if self.providers:
            logger.info(
                "AI providers ready: %s (preferred=%s)",
                [name for name, _ in self.providers],
                self.settings.ai_provider,
            )
        else:
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
        local_topics: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not content.strip():
            raise ExternalServiceError("No text content to analyze")

        extracted_topics_hint = ""
        if local_topics and local_topics.get("syllabus_topics"):
            extracted_topics_hint = "\n".join(
                f"- {t} (freq: {local_topics.get('topic_frequency', {}).get(t, '?')})"
                for t in local_topics["syllabus_topics"][:30]
            )

        if should_skip_pyq_llm(local_topics):
            logger.info("PYQ analysis: using local pipeline only (skipping LLM validation)")
            result = sanitize_analysis_result(local_topics or {})
            metadata = {
                "provider": "local",
                "model": "pipeline",
                "tokens_used": None,
                "prompt_version": PROMPT_VERSION,
                "llm_skipped": True,
            }
            return result, metadata

        if self.ai_available:
            try:
                result, metadata = await self.llm_service.analyze_pyq_with_llm(
                    content,
                    subject,
                    num_documents=num_documents,
                    extracted_topics_hint=extracted_topics_hint or "None pre-extracted",
                )
                result = sanitize_analysis_result(result)
                if local_topics and local_topics.get("topic_table"):
                    from app.services.pipeline.notes_pipeline import NotesPipeline

                    result = NotesPipeline().merge_ai_analysis(local_topics, result)
                elif not result.get("topic_table"):
                    local = analyze_pyq_local(content, subject)
                    for key in (
                        "topic_table", "academic_topic_table", "most_important_topics",
                        "frequently_asked_topics", "rarely_asked_topics", "topic_groups",
                        "syllabus_topics", "topic_frequency", "important_topics",
                    ):
                        result.setdefault(key, local.get(key, [] if key != "topic_frequency" else {}))
                metadata["llm_skipped"] = False
                return result, metadata
            except Exception as exc:
                logger.error("PYQ analysis AI failed, falling back to local: %s", exc)

        from app.services.pipeline.notes_pipeline import NotesPipeline
        from app.utils.topic_analysis import build_consolidated_analysis

        pipeline = NotesPipeline()
        if local_topics and local_topics.get("topic_table"):
            result = sanitize_analysis_result(local_topics)
        else:
            pipeline_result = pipeline.run(content, subject=subject, num_documents=num_documents)
            result = pipeline_result.topic_analysis or build_consolidated_analysis(
                pipeline_result.cleaned_text,
                subject=subject,
                num_documents=num_documents,
            )
        metadata = {
            "provider": "local",
            "model": "pipeline",
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
        subject_label = subject or "engineering"
        material = self._usable_study_material(rag_context)

        structured: dict[str, Any] = {
            "topic": topic,
            "whatIsIt": (
                f"Think of **{topic}** as a core idea in {subject_label}. "
                f"In simple words, it is the set of principles and techniques used to understand "
                f"and solve problems that involve {topic}. "
                f"You do not need fancy jargon yet — start by asking: what problem does {topic} fix, "
                f"and what steps does it follow?"
            ),
            "whyNeeded": (
                f"Without **{topic}**, students often jump into formulas or code with no mental model. "
                f"Exams and labs expect you to explain why {topic} exists, how it works, and when to use it. "
                f"This section exists so you can answer that 'why' confidently."
            ),
            "realLifeAnalogy": (
                f"Imagine a school library. Students (requests) need books (resources). "
                f"**{topic}** is like the librarian's system that decides how books are found, lent, "
                f"and returned so the library stays usable — even when many students arrive at once."
            ),
            "coreConcept": (
                f"1. Name the goal of **{topic}**\n"
                f"2. List its main parts / ideas\n"
                f"3. Connect each part to the problem it solves\n"
                f"4. Only then move to formulas, diagrams, or code"
            ),
            "howItWorks": (
                f"1. Identify the input / situation where {topic} is used\n"
                f"2. Apply the main rule or mechanism of {topic}\n"
                f"3. Follow each intermediate step in order\n"
                f"4. Check the final result against the goal"
            ),
            "architecture": f"At a high level, {topic} has a goal, a few cooperating parts, and a clear flow from input to result.",
            "components": [
                {
                    "name": "Goal",
                    "purpose": f"States what {topic} is trying to achieve",
                    "responsibility": "Keeps the answer focused",
                    "interaction": "Guides every later step",
                    "simpleExplanation": "The 'why we are here' of the topic",
                },
                {
                    "name": "Mechanism",
                    "purpose": f"Shows how {topic} actually operates",
                    "responsibility": "Produces the working steps",
                    "interaction": "Uses the goal and feeds the example",
                    "simpleExplanation": "The engine of the concept",
                },
            ],
            "diagram": (
                f"Problem\n"
                f"   |\n"
                f"Need for {topic}\n"
                f"   |\n"
                f"Core idea + steps\n"
                f"   |\n"
                f"Example / result"
            ),
            "realWorldExample": (
                material
                or (
                    f"Exam walkthrough: define {topic} in one sentence, write 4–5 working steps, "
                    f"then finish with one short example and one limitation."
                )
            ),
            "deepDive": (
                material
                or (
                    f"For university depth on **{topic}**: pair the simple story with precise terms, "
                    f"show one comparison with a related concept, and note where students confuse terms."
                )
            ),
            "advantages": [
                f"Gives a clear mental model for {topic} — so answers stay structured",
                "Supports definition + working + example exam patterns",
            ],
            "disadvantages": [
                f"Local fallback notes are thinner than full AI lectures — configure GEMINI_API_KEY for full Professor Alex notes",
            ],
            "comparison": {
                "title": f"{topic} vs related idea",
                "headers": ["Aspect", topic, "Related concept"],
                "rows": [
                    ["Focus", f"Core idea of {topic}", "Often confused neighbour topic"],
                    ["Exam tip", "Definition + working", "Know the difference clearly"],
                ],
            },
            "commonMistakes": [
                f"Memorising only the name of {topic} without working steps — happens when students skip 'how it works'",
                f"Mixing {topic} with a closely related concept — happens when comparison is never practised",
            ],
            "vivaQuestions": [
                {"question": f"What is {topic} in one sentence?", "answer": f"A core {subject_label} idea used to handle problems involving {topic}."},
                {"question": f"Why do we need {topic}?", "answer": f"It solves a practical problem and gives a repeatable method for {topic}-related questions."},
                {"question": f"How does {topic} work?", "answer": "State the goal, list ordered stages, and end with the expected result."},
                {"question": "What should you write first in a long answer?", "answer": "Simple meaning, then why needed, then working steps, then example."},
            ],
            "examQuestions": {
                "longAnswer": [
                    {
                        "question": f"Explain {topic} with a neat diagram and one example.",
                        "answer": f"Start with What is it?, Why needed?, How it works (numbered), one ASCII diagram, one example, close with one limitation.",
                    }
                ],
                "shortAnswer": [
                    {"question": f"Define {topic}.", "answer": f"**{topic}** is a {subject_label} concept for solving problems related to {topic}."},
                    {"question": f"List two advantages of {topic}.", "answer": "Clear mental model; structured exam answers (definition + working + example)."},
                ],
            },
            "mcqs": [
                {
                    "question": f"What should come first when explaining {topic}?",
                    "options": ["Random formulas", "Simple meaning + why it exists", "Only disadvantages", "Only MCQ options"],
                    "answer": "B",
                    "explanation": "Understanding starts with meaning and purpose, then mechanism.",
                }
            ],
            "memoryTricks": [
                f"W-C-H-E for {topic}: What → Why → How → Example",
            ],
            "revisionSheet": [
                f"**{topic}** = core {subject_label} idea",
                "What is it? (simple)",
                "Why needed? (problem it solves)",
                "Analogy helps memory",
                "Core concept in small parts",
                "How it works = numbered steps",
                "One real example",
                "Know advantages + trade-offs",
                "Compare with related concept",
                "Revise viva + 1 long answer",
            ],
            "keyTakeaways": [
                f"⭐⭐⭐ Must Know — simple meaning of **{topic}**",
                f"⭐⭐⭐ Must Know — why {topic} exists + how it works",
                f"⭐⭐ Important — one example + common mistakes",
                f"⭐ Good to Know — comparison / limitations",
            ],
        }

        notes = format_exam_notes_markdown(structured)
        meta: dict[str, Any] = {
            "provider": "local",
            "model": "rule-based",
            "prompt_version": PROMPT_VERSION,
            "rag_chunk_count": 1 if material else 0,
            "generation_mode": "local_fallback",
            "notes_engine": "professor_alex_v18",
        }
        return {
            "notes": notes,
            "summary": f"Professor Alex lecture notes for {topic}. Configure GEMINI_API_KEY for full AI notes.",
            "structured": structured,
        }, meta

    @staticmethod
    def _usable_study_material(rag_context: str, *, limit: int = 1800) -> str:
        """Turn retrieved snippets into readable teaching paragraphs (no instruction stubs)."""
        if not rag_context or not rag_context.strip():
            return ""
        chunks: list[str] = []
        for raw in re.split(r"\n\s*---\s*\n|\n{2,}", rag_context):
            text = sanitize_note_text(raw).strip()
            if len(text) < 40:
                continue
            if re.match(
                r"^(explain|provide|discuss|write|describe|cover|include)\b",
                text,
                re.I,
            ):
                continue
            chunks.append(text)
            if sum(len(c) for c in chunks) >= limit:
                break
        if not chunks:
            return ""
        joined = "\n\n".join(chunks)
        return joined[:limit].rstrip()

    def _normalize_topic_result(self, result: dict[str, Any], *, topic: str = "") -> dict[str, Any]:
        """Normalize LLM JSON through the exam-notes postprocess pipeline."""
        pipeline = ExamNotesPipeline(max_retries=1)
        try:
            processed = pipeline.postprocess(result, topic=topic)
            return {
                "notes": clean_notes_markdown(processed["notes"]),
                "summary": clean_notes_markdown(str(processed.get("summary") or "")).strip() or None,
                "structured": processed.get("structured"),
                "quality": processed.get("quality"),
            }
        except Exception:
            # Legacy structured / plain markdown fallback for unexpected shapes
            if is_structured_notes_result(result):
                structured = extract_structured_payload(result)
                if topic and not structured.get("topic"):
                    structured["topic"] = topic
                notes = structured_notes_to_markdown(structured)
                summary = clean_notes_markdown(
                    str(structured.get("summary") or result.get("summary") or "")
                ).strip()
                return {
                    "notes": clean_notes_markdown(notes),
                    "summary": summary or None,
                    "structured": structured,
                }

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
            return {"notes": notes, "summary": summary or None, "structured": None}

    async def generate_topic_notes(
        self,
        topic: str,
        *,
        rag_context: str = "",
        analysis_context: str = "",
        subject: str | None = None,
        rag_sources: list[dict[str, Any]] | None = None,
        pipeline_context: str = "",
        exam_priority: str = "",
        pyq_questions: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.ai_available:
            logger.warning("Notes local fallback — no AI provider configured for topic=%s", topic)
            result, meta = self._local_topic_notes(
                topic, subject, rag_context=rag_context, analysis_context=analysis_context
            )
            if rag_sources:
                meta["rag_sources"] = rag_sources[:8]
            return result, meta

        async def _generate_json(system_prompt: str, user_prompt: str):
            return await self.llm_service._generate_json(
                system_prompt,
                user_prompt,
                max_output_tokens=GEMINI_MAX_NOTES_TOKENS,
                temperature=0.3,
                top_p=0.9,
            )

        try:
            pipeline = ExamNotesPipeline(max_retries=2)
            result, metadata = await pipeline.run(
                topic=topic,
                generate_json=_generate_json,
                rag_context=rag_context,
                analysis_context=analysis_context,
                subject=subject,
                exam_priority=exam_priority,
                pyq_questions=pyq_questions,
                pipeline_context=pipeline_context,
            )
            result["notes"] = clean_notes_markdown(result.get("notes") or "")
            if not result["notes"]:
                raise ExternalServiceError("AI returned empty notes content")
            if is_placeholder_notes(result["notes"]):
                raise ExternalServiceError(
                    "AI returned instruction placeholders instead of study notes"
                )

            if rag_sources:
                metadata["rag_sources"] = rag_sources[:8]
                metadata["rag_chunk_count"] = metadata.get("rag_chunk_count") or len(rag_sources)
            metadata["generation_mode"] = "rag" if rag_context.strip() else "ai_only"
            if result.get("structured"):
                metadata["structured_notes"] = result["structured"]
            return result, metadata
        except Exception as exc:
            logger.error("Exam notes pipeline failed topic=%s: %s", topic, exc)
            result, meta = self._local_topic_notes(
                topic, subject, rag_context=rag_context, analysis_context=analysis_context
            )
            meta["generation_error"] = _friendly_ai_error(str(exc))
            meta["ai_error"] = str(exc)
            if rag_sources:
                meta["rag_sources"] = rag_sources[:8]
            return result, meta

    async def stream_topic_notes(
        self,
        topic: str,
        *,
        rag_context: str = "",
        analysis_context: str = "",
        subject: str | None = None,
        pipeline_context: str = "",
        exam_priority: str = "",
        pyq_questions: str = "",
    ):
        """Stream LLM tokens for progressive notes rendering."""
        async for token in self.llm_service.stream_topic_notes_tokens(
            topic,
            rag_context=rag_context,
            analysis_context=analysis_context,
            subject=subject,
            pipeline_context=pipeline_context,
            exam_priority=exam_priority,
            pyq_questions=pyq_questions,
        ):
            yield token

    def _normalize_batch_notes_result(
        self,
        result: dict[str, Any],
        topics: list[str],
    ) -> dict[str, Any]:
        topic_notes = result.get("topic_notes")
        if isinstance(topic_notes, list) and topic_notes:
            sections: list[str] = []
            for entry in topic_notes:
                if isinstance(entry, dict) and is_structured_notes_result(entry):
                    sections.append(structured_notes_to_markdown(entry))
                elif isinstance(entry, dict):
                    title = entry.get("topic") or "Topic"
                    body = entry.get("notes") or entry.get("content") or ""
                    if body:
                        sections.append(f"# {title}\n\n{body}")
            if sections:
                content = clean_notes_markdown("\n\n".join(sections))
                return {
                    "title": result.get("title") or "Generated Notes",
                    "content": content,
                    "summary": clean_notes_markdown(str(result.get("summary") or "")).strip() or None,
                    "topics": result.get("topics") or topics,
                }

        content = result.get("content") or result.get("notes") or ""
        return {
            "title": result.get("title") or "Generated Notes",
            "content": clean_notes_markdown(str(content)),
            "summary": clean_notes_markdown(str(result.get("summary") or "")).strip() or None,
            "topics": result.get("topics") or topics,
        }

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
            result, metadata = await self._generate_json_with_fallback(
                NOTES_GENERATE_SYSTEM_PROMPT,
                user_prompt,
                max_output_tokens=GEMINI_MAX_NOTES_TOKENS,
            )
            return self._normalize_batch_notes_result(result, topics), metadata
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
