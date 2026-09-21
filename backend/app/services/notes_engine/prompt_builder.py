"""Prompt builder for ExamBuddy concise exam notes (v40).

One static system prompt carries the product rules; the user message carries
only Subject + Topic. PYQ text, RAG snippets, and paper wording never reach
the model — a PYQ only ever identifies WHICH topic to write about.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.notes_engine.schema import (
    TARGET_WORD_COUNT_MAX,
    TARGET_WORD_COUNT_MIN,
)

CONCISE_NOTES_SYSTEM_PROMPT = f"""You are ExamBuddy's engineering exam notes generator. You write short, \
exam-ready revision notes for ONE topic of ONE subject.

INPUT: a Subject and a Topic. Nothing else. The topic is a syllabus concept, never a question to answer.

OUTPUT: a JSON object with exactly these fields and nothing else:
- definition: 2-3 sentences. Simple English but technically accurate.
- working: 4-7 short numbered steps explaining how it works. Each step is one line. Include a short \
text flow (e.g. "Input -> Process -> Output") inside a step only when it genuinely clarifies the process.
- advantages: 3-5 concise points.
- disadvantages: 2-4 concise points.
- applications: 3-5 real-world or engineering applications. Each has a short "name" and a one-line \
"detail" explaining where and why it is used.
- example: ONE clear practical or engineering example. If the topic is an algorithm or involves \
mathematics, make it a small worked example with concrete values and the result.
- quick_revision: 4-6 last-minute recall points, each at most about 15 words.

RULES:
- The whole response must be concise: {TARGET_WORD_COUNT_MIN}-{TARGET_WORD_COUNT_MAX} words in total \
across all fields. Brevity matters more than depth.
- Use simple English. Stay technically accurate and adapt the content to the subject's discipline \
(CSE/IT, ECE/EE, Mechanical, Civil, or any other engineering branch).
- Do not add any section beyond the seven fields above.
- Do not generate interview questions, viva questions, MCQs, study tips, or references.
- Do not say the topic is important, frequently asked, scoring, or exam-worthy.
- Do not mention previous year questions, question papers, marks, AI, ExamBuddy, or how these notes \
were produced.
- Do not treat the topic as a question. Never begin with "Explain...", "Discuss...", "Write about...", \
or any similar instruction phrasing.
- Never invent formulas, facts, figures, or applications. If you are not sure a detail is correct, \
leave it out and keep the notes shorter.
- Never repeat the same point in different words, within a field or across fields.
- Write plain sentences. No headings inside field text (the system adds headings), no markdown code \
fences, no meta-commentary.

If the Subject + Topic pair is not a real, teachable engineering concept, return ONLY:
{{"status":"UNKNOWN_TOPIC"}}

Return only the JSON object. No prose around it, no markdown fences.
"""

CONCISE_NOTES_USER_PROMPT = """Subject: {subject}
Topic: {topic}

Write the concise exam notes for this topic as JSON.
"""

CONCISE_REPAIR_SYSTEM_PROMPT = CONCISE_NOTES_SYSTEM_PROMPT + """
You are now fixing a previous response that failed validation. Keep every correct field, fix only what \
the errors list mentions, and keep the total length within the word target.
"""

CONCISE_REPAIR_USER_PROMPT = """Subject: {subject}
Topic: {topic}

Your previous JSON failed validation:
{errors}

Previous JSON:
{draft}

Return the corrected JSON object.
"""


def normalize_exam_priority(exam_priority: str = "", *, frequency: int | None = None) -> str:
    """Map frequency / legacy labels to a clean Exam Priority value.

    Kept for callers that still track priority for ordering and analytics. It
    is deliberately NOT part of the notes prompt: concise notes have one fixed
    depth, and priority wording is exactly the kind of meta the notes must
    never contain.
    """
    raw = (exam_priority or "").strip().lower()
    if frequency is not None:
        if frequency >= 3:
            return "High"
        if frequency == 2:
            return "Medium"
        if frequency == 1:
            return "Low"
    if not raw:
        return "Standard"
    if "high" in raw or "frequent" in raw or "⭐" in (exam_priority or ""):
        return "High"
    if "medium" in raw or "often" in raw:
        return "Medium"
    if "low" in raw or "rare" in raw:
        return "Low"
    if raw in {"high", "medium", "low", "standard"}:
        return raw[:1].upper() + raw[1:]
    cleaned = re.sub(r"\b(q\d+|marks?|paper|code)\b", "", raw, flags=re.I).strip()
    if "frequent" in cleaned or "high" in cleaned:
        return "High"
    if "often" in cleaned or "medium" in cleaned:
        return "Medium"
    return "Standard"


def is_unknown_topic_payload(data: dict | None) -> bool:
    """True when the model refused an ambiguous / non-engineering topic."""
    if not data or not isinstance(data, dict):
        return False
    status = str(data.get("status") or "").strip().upper()
    topic = str(data.get("topic") or "").strip().upper()
    return status == "UNKNOWN_TOPIC" or topic == "UNKNOWN_TOPIC"


def clean_topic(topic: str) -> str:
    """Strip question phrasing so a PYQ-derived topic reads as a concept.

    Stage 2 usually hands over a clean textbook name, but PYQ-sourced topics
    occasionally arrive as "Explain paging in OS" — the notes must be about
    the concept, not the question.
    """
    text = " ".join((topic or "").split())
    text = re.sub(
        r"^(explain|discuss|describe|define|write\s+(a\s+)?(short\s+)?note[s]?\s+on|"
        r"what\s+is|what\s+are|state|list|elaborate|illustrate|give)\b[:,]?\s*",
        "",
        text,
        flags=re.I,
    ).strip()
    text = re.sub(r"\s*(with|using)\s+(a\s+)?(suitable\s+)?(neat\s+)?(diagram|example)s?\.?$", "", text, flags=re.I)
    return text.strip(" .:-?") or " ".join((topic or "").split())


def build_concise_notes_prompts(*, topic: str, subject: str | None = None) -> tuple[str, str]:
    """Return (system prompt, user prompt) for the single concise notes call."""
    user = CONCISE_NOTES_USER_PROMPT.format(
        subject=(subject or "General").strip() or "General",
        topic=clean_topic(topic) or "Topic",
    )
    return CONCISE_NOTES_SYSTEM_PROMPT, user


def build_concise_repair_prompts(
    *,
    topic: str,
    subject: str | None = None,
    errors: list[Any] | str | None = None,
    draft: Any = None,
) -> tuple[str, str]:
    """Build the one-shot repair prompt used when validation fails."""
    if isinstance(errors, list):
        errors_text = json.dumps(errors, ensure_ascii=False, indent=2)
    else:
        errors_text = str(errors or "validation failed")

    if isinstance(draft, (dict, list)):
        draft_text = json.dumps(draft, ensure_ascii=False, indent=2)
    else:
        draft_text = str(draft or "{}")
    if len(draft_text) > 6000:
        draft_text = draft_text[:6000] + "\n…(truncated)"

    user = CONCISE_REPAIR_USER_PROMPT.format(
        subject=(subject or "General").strip() or "General",
        topic=clean_topic(topic) or "Topic",
        errors=errors_text,
        draft=draft_text,
    )
    return CONCISE_REPAIR_SYSTEM_PROMPT, user
