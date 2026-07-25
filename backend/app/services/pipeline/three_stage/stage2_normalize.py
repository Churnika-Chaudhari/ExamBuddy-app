"""
Stage 2 — Topic normalization to standard engineering textbook names.

Purpose:
  Convert raw Stage 1 topic names into canonical syllabus terminology.

Inputs:
  - Stage 1 topic list (names + frequencies) — no raw PYQ text

Outputs:
  - Normalized topic names + original→normalized mapping
  - UNKNOWN_TOPIC when confidence is low (never guess)

Isolation rules:
  - Never generates study notes.
  - Downstream Stage 3 notes reuse this mapping when analysis_id is present.

Failure modes:
  - Low-confidence topics → UNKNOWN_TOPIC (filtered from public tables)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.services.pipeline.three_stage.models import Stage1Result, Stage2Result, TopicItem

logger = logging.getLogger("exambuddy.pipeline.stage2")

UNKNOWN_TOPIC = "UNKNOWN_TOPIC"

STAGE2_SYSTEM_PROMPT = """You are an engineering syllabus topic normalizer.

SINGLE RESPONSIBILITY:
Convert each raw topic name into a standard engineering textbook topic name.

Rules:
- Preserve meaning — do not change the concept
- Use standard university / textbook terminology
- Do NOT invent new topics
- Do NOT guess when unsure
- Keep the SAME number of topics, same order
- Keep the same frequency values
- If a topic cannot be normalized confidently, set name to "UNKNOWN_TOPIC"

Examples:
- "Software Architects Roles" → "Roles and Responsibilities of a Software Architect"
- "Reference architecture" → "Reference Architecture"
- "Pipe & Filter" → "Pipe-and-Filter Architectural Pattern"
- "Naive bayes" → "Naive Bayes Classifier"

Return ONLY valid JSON:
{
  "topics": [
    {
      "original": "raw name",
      "name": "Normalized Textbook Name OR UNKNOWN_TOPIC",
      "frequency": 1,
      "confidence": "high|low"
    }
  ]
}
"""

STAGE2_USER_PROMPT = """Normalize these engineering topics to standard textbook names.
Subject: {subject}

Topics JSON:
{topics_json}

Return JSON only. Use UNKNOWN_TOPIC when not confident. Do not generate notes.
"""

# High-confidence alias rules (pattern → textbook name).
_ALIAS_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^\s*pipe\s*(&|and)\s*filter(?:\s+(architecture|pattern|style))?\s*$", re.I),
        "Pipe-and-Filter Architectural Pattern",
    ),
    (
        re.compile(r"^\s*reference\s+architectures?\s*$", re.I),
        "Reference Architecture",
    ),
    (
        re.compile(
            r"^\s*(?:roles?(?:\s+(?:and|&)\s+responsibilities?)?|responsibilities?)\s+"
            r"(?:of\s+)?(?:a\s+)?software\s+architects?\s*$|"
            r"^\s*software\s+architects?\s+(?:roles?|responsibilities?)\s*$",
            re.I,
        ),
        "Roles and Responsibilities of a Software Architect",
    ),
    (
        re.compile(r"^\s*naive\s*-?\s*bayes(?:\s+classifier)?\s*$", re.I),
        "Naive Bayes Classifier",
    ),
    (
        re.compile(r"^\s*client\s*[-/]?\s*server(?:\s+architecture)?\s*$", re.I),
        "Client-Server Architecture",
    ),
    (
        re.compile(r"^\s*mvc(?:\s+architecture)?\s*$", re.I),
        "Model-View-Controller (MVC) Architecture",
    ),
    (
        re.compile(r"^\s*virtual\s+memory\s*$", re.I),
        "Virtual Memory",
    ),
    (
        re.compile(r"^\s*dead\s*-?\s*locks?\s*$", re.I),
        "Deadlock",
    ),
    (
        re.compile(r"^\s*http\s*/?\s*https\s*$", re.I),
        "HTTP and HTTPS",
    ),
)

# Noise / non-topics that must never become notes subjects.
_REJECT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*$"),
    re.compile(r"^\d{3,6}$"),  # subject/paper codes
    re.compile(r"^\s*(q|question)\s*\d+", re.I),
    re.compile(r"^\s*\[?\d+\s*marks?\]?\s*$", re.I),
    re.compile(r"^\s*(max\.?\s*marks?|time\s*:|semester|cbcs)\b", re.I),
    re.compile(r"^\s*(explain|define|describe|write|discuss|compare|differentiate)\b", re.I),
    re.compile(r"^[^a-zA-Z]*$"),
)

_SMALL_WORDS = {
    "and", "or", "of", "the", "a", "an", "in", "on", "for", "to", "with", "vs", "via",
}


@dataclass
class NormalizationOutcome:
    original: str
    normalized: str
    confidence: str  # high | low
    unknown: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "normalized": self.normalized,
            "confidence": self.confidence,
            "unknown": self.unknown,
        }


def _is_reject(name: str) -> bool:
    text = (name or "").strip()
    if len(text) < 3:
        return True
    return any(p.search(text) for p in _REJECT_PATTERNS)


def _token_count(name: str) -> int:
    return len([t for t in re.split(r"[\s/_-]+", name.strip()) if t])


def _title_cleanup(name: str) -> str:
    text = re.sub(r"\s+", " ", (name or "").strip())
    text = text.replace("_", " ")
    words: list[str] = []
    for idx, w in enumerate(text.split(" ")):
        if not w:
            continue
        if w.isupper() and len(w) <= 5:
            words.append(w)
        elif w.lower() in _SMALL_WORDS and idx > 0:
            words.append(w.lower())
        else:
            words.append(w[:1].upper() + w[1:].lower() if w.islower() or w.isupper() else w[:1].upper() + w[1:])
    if words:
        words[0] = words[0][:1].upper() + words[0][1:]
    return " ".join(words).strip()


def _token_has_vowel(token: str) -> bool:
    return bool(re.search(r"[aeiouAEIOU]", token))


def _looks_like_textbook_topic(name: str) -> bool:
    """Conservative check: already a plausible syllabus topic phrase."""
    text = (name or "").strip()
    if _is_reject(text):
        return False
    tokens = [t for t in re.split(r"[\s/_-]+", text) if t]
    if len(tokens) < 2:
        return False
    if len(text) > 90:
        return False
    if re.match(
        r"^(explain|define|describe|write|discuss|compare|differentiate|what|why|how)\b",
        text,
        re.I,
    ):
        return False
    # Reject nonsense tokens (no vowels) unless short acronyms
    for tok in tokens:
        letters = "".join(ch for ch in tok if ch.isalpha())
        if not letters:
            continue
        if len(letters) <= 4 and letters.isupper():
            continue
        if len(letters) >= 4 and not _token_has_vowel(letters):
            return False
    letters = sum(ch.isalpha() for ch in text)
    return letters >= 6


def normalize_topic_name_local(name: str) -> NormalizationOutcome:
    """
    Deterministic normalization with confidence.

    Returns UNKNOWN_TOPIC when not confident (no guessing).
    """
    original = (name or "").strip()
    if _is_reject(original):
        return NormalizationOutcome(
            original=original,
            normalized=UNKNOWN_TOPIC,
            confidence="low",
            unknown=True,
        )

    for pattern, replacement in _ALIAS_RULES:
        if pattern.fullmatch(original):
            return NormalizationOutcome(
                original=original,
                normalized=replacement,
                confidence="high",
                unknown=False,
            )

    cleaned = _title_cleanup(original)
    # Accept only when the phrase already looks like a syllabus topic and
    # cleanup is essentially casing/spacing (meaning preserved, not invented).
    if _looks_like_textbook_topic(cleaned):
        compact_orig = re.sub(r"[^a-z0-9]+", "", original.lower())
        compact_clean = re.sub(r"[^a-z0-9]+", "", cleaned.lower())
        if compact_orig == compact_clean or compact_orig in compact_clean or compact_clean in compact_orig:
            return NormalizationOutcome(
                original=original,
                normalized=cleaned,
                confidence="high",
                unknown=False,
            )

    return NormalizationOutcome(
        original=original,
        normalized=UNKNOWN_TOPIC,
        confidence="low",
        unknown=True,
    )


def normalize_topics_local(stage1: Stage1Result) -> Stage2Result:
    mapping: dict[str, str] = {}
    topics: list[TopicItem] = []
    unknown = 0
    for item in stage1.topics:
        outcome = normalize_topic_name_local(item.name)
        mapping[item.name] = outcome.normalized
        if outcome.unknown:
            unknown += 1
            continue
        topics.append(TopicItem(name=outcome.normalized, frequency=item.frequency))
    return Stage2Result(
        subject=stage1.subject,
        topics=topics,
        mapping=mapping,
        metadata={
            "stage": 2,
            "provider": "local",
            "unknown_topics": unknown,
        },
    )


def _apply_ai_mapping(
    stage1: Stage1Result,
    ai_topics: list[dict[str, Any]],
) -> Stage2Result | None:
    if not ai_topics or len(ai_topics) != len(stage1.topics):
        return None
    mapping: dict[str, str] = {}
    out: list[TopicItem] = []
    unknown = 0
    for original, row in zip(stage1.topics, ai_topics, strict=True):
        if not isinstance(row, dict):
            return None
        new_name = str(row.get("name") or "").strip()
        confidence = str(row.get("confidence") or "").strip().lower()
        if not new_name:
            return None
        if new_name.upper() == UNKNOWN_TOPIC or confidence == "low":
            mapping[original.name] = UNKNOWN_TOPIC
            unknown += 1
            continue
        # Prefer local high-confidence alias if AI drifts
        local = normalize_topic_name_local(original.name)
        final_name = local.normalized if local.confidence == "high" and not local.unknown else new_name
        if final_name.upper() == UNKNOWN_TOPIC:
            mapping[original.name] = UNKNOWN_TOPIC
            unknown += 1
            continue
        mapping[original.name] = final_name
        out.append(TopicItem(name=final_name, frequency=original.frequency))
    return Stage2Result(
        subject=stage1.subject,
        topics=out,
        mapping=mapping,
        metadata={"stage": 2, "provider": "ai", "unknown_topics": unknown},
    )


async def normalize_topics_with_ai(
    stage1: Stage1Result,
    *,
    generate_json,
) -> Stage2Result | None:
    if not stage1.topics or generate_json is None:
        return None
    import json

    topics_json = json.dumps(stage1.as_dict()["topics"], ensure_ascii=True)
    user = STAGE2_USER_PROMPT.format(subject=stage1.subject, topics_json=topics_json)
    try:
        raw, meta = await generate_json(STAGE2_SYSTEM_PROMPT, user)
    except Exception as exc:
        logger.warning("Topic normalization AI failed: %s", exc)
        return None
    if not isinstance(raw, dict):
        return None
    applied = _apply_ai_mapping(stage1, list(raw.get("topics") or []))
    if not applied:
        return None
    applied.metadata.update(
        {
            "provider": (meta or {}).get("provider", "ai"),
            "model": (meta or {}).get("model"),
        }
    )
    return applied


def _collapse_duplicate_names(topics: list[TopicItem]) -> list[TopicItem]:
    merged: dict[str, TopicItem] = {}
    order: list[str] = []
    for item in topics:
        if item.name.upper() == UNKNOWN_TOPIC:
            continue
        key = item.name.casefold()
        if key not in merged:
            merged[key] = TopicItem(name=item.name, frequency=item.frequency)
            order.append(key)
        else:
            merged[key].frequency += item.frequency
    return [merged[k] for k in order]


async def run_stage2(
    stage1: Stage1Result,
    *,
    generate_json=None,
) -> Stage2Result:
    """
    Normalize Stage 1 topics to textbook names.
    Drops UNKNOWN_TOPIC entries from the analysis topic list.
    Never invents topics.
    """
    local = normalize_topics_local(stage1)
    result = local
    if generate_json is not None and stage1.topics:
        ai_result = await normalize_topics_with_ai(stage1, generate_json=generate_json)
        if ai_result is not None:
            logger.info(
                "Stage 2 AI normalized kept=%d unknown=%s",
                len(ai_result.topics),
                ai_result.metadata.get("unknown_topics"),
            )
            result = ai_result
        else:
            logger.info("Stage 2 local normalized kept=%d", len(local.topics))
    else:
        logger.info("Stage 2 local normalized kept=%d", len(local.topics))

    collapsed = _collapse_duplicate_names(result.topics)
    if len(collapsed) != len(result.topics):
        result.metadata["collapsed_duplicates"] = len(result.topics) - len(collapsed)
        result.topics = collapsed
    return result


def lookup_stage2_topic(
    raw_topic: str,
    analysis_doc: dict[str, Any] | None,
) -> str | None:
    """
    Resolve a topic name from a completed analysis Stage 2 mapping.

    Returns the normalized textbook name when found, else None.
    """
    if not analysis_doc or not raw_topic:
        return None
    original = raw_topic.strip()
    if not original:
        return None

    stage2 = analysis_doc.get("stage2_topics") or {}
    if not isinstance(stage2, dict):
        return None

    mapping = stage2.get("mapping") or {}
    if isinstance(mapping, dict):
        # Exact key match first.
        if original in mapping:
            mapped = str(mapping[original] or "").strip()
            if mapped and mapped.upper() != UNKNOWN_TOPIC:
                return mapped
        # Case-insensitive key match.
        lower = original.lower()
        for key, value in mapping.items():
            if str(key).strip().lower() == lower:
                mapped = str(value or "").strip()
                if mapped and mapped.upper() != UNKNOWN_TOPIC:
                    return mapped

    # Match normalized topic rows from Stage 2 tables.
    for row in stage2.get("topics") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("topic") or "").strip()
        orig = str(row.get("original") or "").strip()
        if name and (
            name.lower() == original.lower()
            or (orig and orig.lower() == original.lower())
        ):
            if name.upper() != UNKNOWN_TOPIC:
                return name

    # Match topic_frequency_table rows (post-analysis public shape).
    for row in analysis_doc.get("topic_frequency_table") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("topic") or "").strip()
        if name.lower() == original.lower() and name.upper() != UNKNOWN_TOPIC:
            return name

    return None


async def normalize_single_topic(
    topic: str,
    *,
    subject: str | None = None,
    generate_json=None,
) -> str:
    """
    Normalize one topic for notes generation.

    Returns a textbook topic name, or UNKNOWN_TOPIC when not confident.
    """
    original = (topic or "").strip()
    if not original:
        return UNKNOWN_TOPIC

    # Fast path: high-confidence local alias / clean syllabus phrase
    local = normalize_topic_name_local(original)
    if not local.unknown and local.confidence == "high":
        return local.normalized

    # AI path for borderline cases
    if generate_json is not None:
        stage1 = Stage1Result(
            subject=(subject or "General").strip() or "General",
            topics=[TopicItem(name=original, frequency=1)],
        )
        ai_result = await normalize_topics_with_ai(stage1, generate_json=generate_json)
        if ai_result and ai_result.mapping.get(original):
            mapped = ai_result.mapping[original]
            if mapped and mapped.upper() != UNKNOWN_TOPIC:
                return mapped
            return UNKNOWN_TOPIC
        if ai_result and ai_result.topics:
            return ai_result.topics[0].name

    return UNKNOWN_TOPIC
