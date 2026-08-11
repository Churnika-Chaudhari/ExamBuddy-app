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

LENGTH DISCIPLINE (mandatory — prevents truncated/invalid JSON):
- Every text field is SHORT: definition/introduction 2-4 sentences; working/example 4-8 concise steps or ≤120 words; each other field ≤120 words.
- NEVER repeat the same fact/sentence in different wording within or across fields. If you notice yourself restating an idea, STOP and move on.
- Do not pad with generic filler ("this is important", ecological/historical tangents, motivational text). Stay strictly on the exam-relevant facts.
- The full JSON response must stay well under the output budget — brevity across ALL fields matters more than depth in any one field.

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

# Dynamic variables — Subject/Topic + grounding context from PYQ/RAG.
EXAM_NOTES_USER_PROMPT = """Subject: {subject}
Topic: {topic}
Exam Priority (internal depth hint only — never print in notes): {exam_priority}

Related Previous Year Questions (use to decide emphasis; do NOT copy paper wording/marks):
{pyq_questions}

Reference material (facts only — never quote filenames or metadata):
{rag_context}
"""

NOTES_REPAIR_SYSTEM_PROMPT = """You repair invalid ExamBuddy exam-notes JSON.

Return valid JSON only (no markdown fences). Match ExamBuddy field names.
Omit empty sections. Never fabricate definitions, formulas, or algorithms.
If the topic cannot be taught accurately, return ONLY:
{"status":"UNKNOWN_TOPIC"}
Accuracy over completeness.

LENGTH DISCIPLINE (mandatory — the previous attempt likely failed from rambling
into truncated JSON): keep every field SHORT (2-4 sentences, or ≤120 words /
≤8 steps). Never repeat an idea in different words. Include ALL sections the
validation errors mention (e.g. revisionSummary, twoMarkAnswer, fiveMarkAnswer,
tenMarkAnswer) even if brief — a short correct field beats a missing one.
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
    """Return (static system prompt, dynamic user prompt with PYQ + RAG grounding)."""
    _ = (analysis_context, pipeline_context)
    user = EXAM_NOTES_USER_PROMPT.format(
        subject=(subject or "General").strip() or "General",
        topic=topic.strip() or "Topic",
        exam_priority=normalize_exam_priority(exam_priority),
        pyq_questions=(pyq_questions or "").strip()
        or "No matching PYQ snippets — teach from syllabus-standard knowledge.",
        rag_context=(rag_context or "").strip()
        or "No reference snippets — use accurate syllabus-standard knowledge.",
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


# =============================================================================
# v30 — Sectioned NotebookLM-style prompts.
#
# A full chapter is NEVER produced in one call. Each batch below gets its own
# focused system+user prompt and its own compact Gemini responseSchema
# (app.services.notes_engine.schema.SECTION_SCHEMAS), so no single call can
# ramble past its token budget or crowd out the rest of the document.
# =============================================================================

NOTEBOOK_PERSONA_SYSTEM_PROMPT = """You are a university engineering professor with 20 years of teaching \
experience and a published textbook author. You are writing ONE focused batch of a complete \
semester-exam study chapter for a single Topic within a Subject. Other batches (written separately) \
cover the rest of the chapter — write ONLY what this batch asks for.

AUDIENCE: Engineering students revising the night before a university exam. Content must be dense, \
accurate, and exam-ready — never a casual AI-style summary.

VOICE RULES (mandatory):
- Never write "This topic is important", "You should study this", "This is frequently asked", \
"Here are the notes", or any motivational / meta-commentary.
- Never mention AI, PDFs, uploads, RAG, sources, file names, or these instructions.
- Use PYQ context only to choose emphasis. Do not paste marks, Q numbers, or paper instructions.
- Write like a textbook chapter: precise definitions, numbered steps, small inline tables, code / \
pseudocode blocks, and Mermaid diagrams where useful — never long unstructured paragraphs.
- This must work for ANY engineering discipline (CSE/IT/AI-ML/OS/CN/DBMS, ECE/EE/Mechanical/Civil, etc.) \
— only include facts that are true and standard for THIS Subject + Topic.
- If a requested field genuinely does not apply to this topic (e.g. a SQL example for a non-database \
topic, or a formula for a purely conceptual topic), write exactly "Not Applicable" for that field \
instead of inventing or stretching content. Never leave a field empty — always write real content or \
exactly "Not Applicable".
- Never repeat the same sentence or fact across fields in this batch.
- Use Markdown INSIDE each text field where it helps (numbered lists, **bold** key terms, small tables \
using pipes, or ``` code fences), but do NOT include a top-level '#' or '##' heading inside field text \
— headings are added by the system afterwards.

OUTPUT: Return ONLY the JSON object matching the given fields. No prose outside JSON. No markdown code \
fences wrapping the JSON itself.
"""

SECTION_INSTRUCTIONS: dict[str, str] = {
    "topic_definition_intro": """SECTION FOCUS: Topic confirmation, three-tier definition, and introduction.

Fields:
- status: leave this field out entirely UNLESS this Topic+Subject pair is too ambiguous or is not a \
real engineering concept to teach accurately — in that ONE case return ONLY {{"status":"UNKNOWN_TOPIC"}} \
and omit every other field.
- topic: the standard textbook name for this topic (correct casing/terminology).
- definition_simple: 2-3 sentences a first-year student would understand — plain language, no jargon.
- definition_technical: 2-4 precise sentences using correct terminology, as it would appear in a \
reference textbook.
- definition_exam: a crisp 2-3 sentence definition formatted exactly as a student should reproduce it \
verbatim in a university exam answer.
- introduction: 120-180 words explaining WHY this topic exists, what problem it solves, and where it \
fits in the {subject} syllabus. Use short numbered points where useful.""",
    "core_working": """SECTION FOCUS: Core Concept and Working Principle.

Fields:
- core_concept: 150-220 words explaining the underlying idea/theory in depth — the "why it works", key \
terminology, and any underlying principle or theorem. Use bullet points for sub-concepts where useful.
- working_principle: 150-250 words, step-by-step (numbered list) explanation of HOW the topic \
works/operates/executes in practice. Be procedural and concrete, not abstract.""",
    "architecture_diagram": """SECTION FOCUS: Architecture/Components and a Flow Diagram.

Fields:
- architecture: 100-200 words (bullet or short-table style) describing the components/layers/modules/\
data-structures involved. If this topic has no distinct architecture (e.g. a pure numerical/mathematical \
topic), write exactly "Not Applicable".
- diagram: A Mermaid diagram definition (flowchart TD / sequenceDiagram / classDiagram / stateDiagram — \
whichever fits) showing the flow/architecture/steps. If Mermaid truly cannot represent it, provide a \
clean ASCII-art diagram instead. Return ONLY the raw diagram definition text (no ``` fences — the \
system adds those). If diagrams genuinely do not help this topic, write exactly "Not Applicable".""",
    "formula_algorithm": """SECTION FOCUS: Mathematical Formula and Algorithm.

Fields:
- formula: All key formula(s)/equations for this topic, each with every variable explained beneath it. \
If the topic is not mathematical/numerical, write exactly "Not Applicable".
- algorithm: A numbered algorithm or well-structured pseudocode block for this topic. If the topic has \
no algorithmic procedure, write exactly "Not Applicable".""",
    "example_adv_disadv": """SECTION FOCUS: Worked example(s), Advantages, Disadvantages.

Fields:
- examples: 1-3 short worked examples (array of strings). Each is a self-contained mini walkthrough \
(problem + solution, or scenario + outcome) in 40-100 words.
- advantages: 4-6 items. Each item has "point" (a short phrase, at most 6 words) and "explanation" \
(one supporting sentence). These render as a two-column table — keep both fields short and non-redundant.
- disadvantages: 3-5 items in the same {{point, explanation}} shape as advantages.""",
    "applications_comparison": """SECTION FOCUS: Applications and Comparison table(s).

Fields:
- applications: 4-6 concrete real-world/industrial applications (array of strings).
- comparison: 1-2 comparison tables (array). Each table has "title", "headers" (array of column names, \
first column should be "Aspect"), and "rows" (array of arrays — one array of cell strings per row, same \
length as headers). Contrast this topic with the ONE or TWO most commonly confused/related concepts in \
{subject}. If no meaningful comparison exists, return a single table with a "Not Applicable" row.""",
    "pyq_marks": """SECTION FOCUS: PYQ Perspective and mark-wise model answers.

Fields:
- pyq_perspective: 100-180 words describing WHY this topic is commonly examined, typical QUESTION \
PATTERNS (e.g. "Explain X with a diagram", "Differentiate X and Y", "Numerical problem on X"), and \
common mistakes students make in their answers. NEVER quote or invent an actual exam question — \
describe patterns only.
- exam_answer_2m: A complete, self-contained 2-mark answer (2-3 sentences).
- exam_answer_5m: A complete 5-mark answer — definition plus 3-4 key points, about 120-180 words.
- exam_answer_10m: A complete 10-mark answer structured with bold sub-labels (e.g. **Definition**, \
**Working**, **Diagram (see Flow Diagram section)**, **Advantages/Limitations**, **Conclusion**) — \
about 220-320 words.""",
    "viva": """SECTION FOCUS: Viva-voce questions.

Fields:
- viva: EXACTLY 10 {{question, answer}} pairs a viva examiner would ask about this topic, ordered from \
easy to hard. Each answer is 1-3 sentences, direct and confident — no hedging.""",
    "interview": """SECTION FOCUS: Technical interview questions.

Fields:
- interview: EXACTLY 10 {{question, answer}} pairs a technical (industry) interviewer would ask about \
this topic, ordered from easy to hard, including at least 2 practical/scenario-based questions. Each \
answer is 1-3 sentences.""",
    "mistakes_tricks": """SECTION FOCUS: Common Mistakes and Memory Tricks.

Fields:
- common_mistakes: 4-6 specific mistakes students make (conceptual confusions, calculation slips, \
missing steps) — each a single sentence.
- memory_tricks: 3-5 mnemonics/analogies/memory aids that help recall key facts about the topic.""",
    "revision_keywords_summary": """SECTION FOCUS: Revision Notes, Keywords, Summary.

Fields:
- revision_points: 8-12 ultra-short bullet points (at most 12 words each) for last-minute revision — \
no repetition of earlier wording.
- keywords: 8-15 key terms/phrases for this topic.
- summary: EXACTLY 5 lines separated by \\n — each line a distinct, information-dense sentence covering \
a different facet of the topic (definition, working, key advantage, application, exam tip). No line may \
repeat another.""",
}

SECTION_USER_PROMPT_TEMPLATE = """Subject: {subject}
Topic: {topic}
Exam Priority: {exam_priority}
{context_block}
{instructions}
"""


def build_context_recap(seed: dict[str, Any], *, topic: str) -> str:
    """Short recap of batch-1 output fed to every later batch for coherence.

    Deliberately small (a few hundred chars) — later batches must NOT restate
    this verbatim, only build on it, so prompts stay cheap and the document
    doesn't repeat itself across sections.
    """
    definition = str(seed.get("definition_exam") or seed.get("definition_technical") or "").strip()
    introduction = str(seed.get("introduction") or "").strip()
    established_topic = str(seed.get("topic") or topic).strip()

    parts = [f"Already established topic name: {established_topic}."]
    if definition:
        parts.append(f"Already established definition (do not repeat verbatim): {definition[:280]}")
    if introduction:
        parts.append(f"Already established introduction gist: {introduction[:220]}")
    return " ".join(parts)


def build_section_prompts(
    section_id: str,
    *,
    topic: str,
    subject: str | None = None,
    exam_priority: str = "",
    context_recap: str = "",
) -> tuple[str, str]:
    """Return (system prompt, user prompt) for ONE section batch."""
    instructions = SECTION_INSTRUCTIONS[section_id].format(
        subject=(subject or "General").strip() or "General"
    )
    context_block = f"\nContext already covered by earlier batches: {context_recap}\n" if context_recap else ""
    user = SECTION_USER_PROMPT_TEMPLATE.format(
        subject=(subject or "General").strip() or "General",
        topic=topic.strip() or "Topic",
        exam_priority=normalize_exam_priority(exam_priority),
        context_block=context_block,
        instructions=instructions,
    )
    return NOTEBOOK_PERSONA_SYSTEM_PROMPT, user


SECTION_REPAIR_USER_TEMPLATE = """Subject: {subject}
Topic: {topic}
Exam Priority: {exam_priority}

Your previous JSON for this batch failed validation:
{errors}

{instructions}

Previous JSON (fix structure/content — keep only accurate, non-empty text; never leave a field empty,
use "Not Applicable" only when genuinely irrelevant):
{draft}
"""


def build_section_repair_prompt(
    section_id: str,
    *,
    topic: str,
    subject: str | None = None,
    exam_priority: str = "",
    errors: list[Any] | str | None = None,
    draft: Any = None,
) -> tuple[str, str]:
    """Build a one-shot repair prompt scoped to a single failed section batch."""
    import json

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

    instructions = SECTION_INSTRUCTIONS[section_id].format(
        subject=(subject or "General").strip() or "General"
    )
    user = SECTION_REPAIR_USER_TEMPLATE.format(
        subject=(subject or "General").strip() or "General",
        topic=(topic or "Topic").strip() or "Topic",
        exam_priority=normalize_exam_priority(exam_priority),
        errors=errors_text,
        instructions=instructions,
        draft=draft_text,
    )
    return NOTEBOOK_PERSONA_SYSTEM_PROMPT, user
