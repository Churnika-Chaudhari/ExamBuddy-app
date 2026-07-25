"""ExamBuddy exam-notes prompt builder — compact system + dynamic user inputs."""

from __future__ import annotations

import re
from typing import Any

from app.services.notes_engine.schema import PROMPT_VERSION

# Static instructions only. Dynamic inputs belong exclusively in the user message.
EXAM_NOTES_SYSTEM_PROMPT = """You are a university engineering professor writing textbook-quality exam notes for ONE topic.

INPUT: Subject, Topic, Exam Priority (High|Medium|Low|Standard). Priority controls depth only — never print it in notes.

OUTPUT: Valid JSON only (no markdown fences). Omit unused/empty fields. Never mention AI, PDFs, PYQs, paper codes, or mark labels outside answer fields.

ACCURACY > COMPLETENESS:
Never fabricate definitions, concepts, formulas, algorithms, complexity, syntax, SQL, architectures, or comparison rows.
Never write generic filler or placeholder text.
If unsure of a fact, omit that section. If topic confidence is low (ambiguous / not a real engineering concept / would require guessing), return ONLY:
{"status":"UNKNOWN_TOPIC"}

FLOW:
1) Detect topicType from Topic+Subject: Theory|Algorithm|Programming|Numerical|Networking|Database|Operating System|AI/ML|Architecture|Electronics|Electrical|Mechanical|Civil|Other
2) Include ONLY relevant sections for that type. Prefer fewer accurate sections over many speculative ones.

SECTIONS (field names exact; omit unused):
definition, introduction, working, architecture, algorithm, formula, diagram, flowchart, pseudocode, syntax, codeExample, sqlExample, example, timeComplexity, spaceComplexity, advantages, disadvantages, applications, comparison, frequentlyAskedQuestions, twoMarkAnswer, fiveMarkAnswer, tenMarkAnswer, revisionSummary

TYPE GUIDES (include type-specific fields only when accurate — never invent to satisfy a type):
- Programming: syntax + codeExample (+output if useful)
- Algorithm: algorithm and/or pseudocode + timeComplexity + spaceComplexity; flowchart/diagram when useful
- Networking: architecture + diagram (Mermaid preferred)
- Database: sqlExample; architecture/diagram when useful
- Numerical: formula with every variable explained
- Theory/Architecture/Other: introduction, working, diagram/applications/comparison when useful
Also prefer when accurate: definition, working/example, FAQs, 2/5/10-mark answers, revisionSummary.

FIELD SHAPES:
- advantages|disadvantages|applications|revisionSummary: string[]
- frequentlyAskedQuestions: [{question, answer}]
- comparison: {title, headers[], rows[][]}  (Comparison Table; only when it aids learning)
- diagram|flowchart: Mermaid preferred, else clean ASCII
- working: numbered steps when natural
- formula: include variable meanings
- topic: standard textbook name; topicType: detected type

Tone: concise textbook, exam-oriented.
"""

# Dynamic variables only — never put static instructions here.
EXAM_NOTES_USER_PROMPT = """Subject: {subject}
Topic: {topic}
Exam Priority: {exam_priority}
"""

NOTES_REPAIR_SYSTEM_PROMPT = """You repair invalid ExamBuddy exam-notes JSON.

Return valid JSON only (no markdown fences). Match ExamBuddy field names.
Omit empty sections. Never fabricate definitions, formulas, or algorithms.
If the topic cannot be taught accurately, return ONLY:
{"status":"UNKNOWN_TOPIC"}
Accuracy over completeness.
"""

NOTES_REPAIR_USER_PROMPT = """Subject: {subject}
Topic: {topic}
Exam Priority: {exam_priority}

Validation errors:
{errors}

Previous JSON (may be invalid — fix structure and types; keep only accurate content):
{draft}
"""


def normalize_exam_priority(exam_priority: str = "", *, frequency: int | None = None) -> str:
    """Map frequency / legacy labels to a clean Exam Priority value."""
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
    """True when the model refused an ambiguous topic."""
    if not data or not isinstance(data, dict):
        return False
    status = str(data.get("status") or "").strip().upper()
    topic = str(data.get("topic") or "").strip().upper()
    return status == "UNKNOWN_TOPIC" or topic == "UNKNOWN_TOPIC"


def build_exam_notes_prompts(
    *,
    topic: str,
    subject: str | None = None,
    rag_context: str = "",
    analysis_context: str = "",
    pipeline_context: str = "",
    exam_priority: str = "",
    pyq_questions: str = "",
) -> tuple[str, str]:
    """Return (static system prompt, dynamic user prompt).

    User message contains only Subject, Topic, and Exam Priority.
    Legacy kwargs (rag/analysis/pipeline/pyq) are ignored for Stage-3 isolation.
    """
    _ = (rag_context, analysis_context, pipeline_context, pyq_questions)
    user = EXAM_NOTES_USER_PROMPT.format(
        subject=(subject or "General").strip() or "General",
        topic=topic.strip() or "Topic",
        exam_priority=normalize_exam_priority(exam_priority),
    )
    return EXAM_NOTES_SYSTEM_PROMPT, user


def build_notes_repair_prompts(
    *,
    topic: str,
    subject: str | None = None,
    exam_priority: str = "",
    errors: list[Any] | str | None = None,
    draft: Any = None,
) -> tuple[str, str]:
    """Build a one-shot repair prompt for invalid notes JSON."""
    import json

    if isinstance(errors, list):
        errors_text = json.dumps(errors, ensure_ascii=False, indent=2)
    else:
        errors_text = str(errors or "schema validation failed")
    if isinstance(draft, (dict, list)):
        draft_text = json.dumps(draft, ensure_ascii=False, indent=2)
    else:
        draft_text = str(draft or "")
    # Bound repair payload size to keep tokens low.
    if len(draft_text) > 12000:
        draft_text = draft_text[:12000] + "\n…(truncated)"
    user = NOTES_REPAIR_USER_PROMPT.format(
        subject=(subject or "General").strip() or "General",
        topic=(topic or "Topic").strip() or "Topic",
        exam_priority=normalize_exam_priority(exam_priority),
        errors=errors_text,
        draft=draft_text or "{}",
    )
    return NOTES_REPAIR_SYSTEM_PROMPT, user


def pipeline_instructions(*, subject: str | None = None) -> str:
    """Deprecated for notes user prompts — kept for import compatibility."""
    _ = subject
    return ""
