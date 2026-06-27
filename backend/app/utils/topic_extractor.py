import re
from collections import Counter
from typing import Any

# Instruction verbs and exam boilerplate — not subject topics
EXAM_STOPWORDS = {
    "explain", "define", "describe", "write", "discuss", "prove", "state", "list",
    "draw", "illustrate", "compare", "differentiate", "distinguish", "enumerate",
    "briefly", "short", "note", "notes", "question", "questions", "answer",
    "answers", "marks", "mark", "section", "paper", "attempt", "total", "following",
    "suitable", "scheme", "information", "technology", "involved", "process",
    "advantages", "disadvantages", "features", "applications", "introduction",
    "functions", "importance", "uses", "mention", "contrast", "similarities",
    "conclusion", "example", "examples", "diagram", "figure", "table", "given",
    "below", "above", "refer", "reference", "university", "examination",
    "examinations", "semester", "course", "code", "date", "time", "hours",
    "minutes", "maximum", "minimum", "each", "part", "parts", "unit", "units",
    "chapter", "chapters", "page", "pages", "student", "students", "college",
    "institute", "department", "subject", "paper", "year", "roll", "number",
    "instructions", "instruction", "attempt", "compulsory", "optional",
    "objective", "subjective", "theory", "practical", "internal", "external",
    "assessment", "evaluation", "grade", "grades", "point", "points", "score",
    "choose", "select", "correct", "incorrect", "true", "false", "option",
    "options", "multiple", "choice", "fill", "blank", "blanks", "match",
    "column", "columns", "pairs", "pair", "solve", "calculate", "compute",
    "derive", "deduce", "show", "prove", "hence", "therefore", "thus",
    "consider", "suppose", "assume", "given", "data", "following", "based",
    "using", "help", "respect", "terms", "term", "define", "meaning", "means",
    "what", "when", "where", "which", "whose", "whom", "how", "why", "whether",
    "does", "do", "did", "has", "have", "had", "will", "would", "could",
    "should", "shall", "may", "might", "must", "being", "been", "were", "was",
    "are", "is", "am", "be", "the", "and", "for", "with", "from", "that",
    "this", "these", "those", "they", "them", "their", "there", "then", "than",
    "also", "only", "just", "very", "much", "more", "most", "some", "any",
    "all", "both", "each", "every", "other", "another", "such", "same",
    "different", "between", "among", "into", "onto", "upon", "over", "under",
    "after", "before", "during", "while", "because", "since", "until", "unless",
    "although", "though", "however", "therefore", "furthermore", "moreover",
    "four", "five", "six", "seven", "eight", "nine", "ten", "first", "second",
    "third", "one", "two", "three", "once", "twice", "half", "full", "whole",
}

# Patterns that indicate exam metadata, not topics
_METADATA_PATTERNS = [
    re.compile(r"^\d+\s*(marks?|m)$", re.I),
    re.compile(r"^(section|part|unit|paper)\s*[a-z0-9]*$", re.I),
    re.compile(r"^(q|question)\s*\d+", re.I),
    re.compile(r"^(i{1,3}|iv|v|vi{0,3}|ix|x)[\).\]]?$", re.I),
]

_QUESTION_PREFIX = re.compile(
    r"^(?:\d+[\).\]]|\([a-z]\)|[Qq]\d+[\).:]|[ivxIVX]+[\).\]])\s*",
    re.I,
)

_INSTRUCTION_SPLIT = re.compile(
    r"\b(?:"
    r"what is|what are|what do you mean by|define|explain|describe|discuss|"
    r"write (?:a |an |the )?(?:short )?(?:note|notes|essay|report) (?:on|about)|"
    r"write (?:a |an )?(?:brief )?(?:note|notes) (?:on|about)|"
    r"compare (?:and contrast )?|differentiate between|distinguish between|"
    r"differentiate|distinguish|list (?:out )?(?:the )?|enumerate|state|prove|"
    r"illustrate (?:with |using )?|briefly explain|with (?:the )?help of|"
    r"write down|give (?:an? )?(?:account|example|reason)|name (?:the )?|"
    r"identify|justify|derive|calculate|compute|solve|sketch|draw (?:a |an |the )?|"
    r"mention|outline|summarize|summarise|highlight|elaborate|analyse|analyze|"
    r"examine|comment on|bring out|bringout"
    r")\b",
    re.I,
)

_MARKS_SUFFIX = re.compile(r"\[?\s*\d+\s*(?:marks?|m)\s*\]?\s*$", re.I)
_TRAILING_PUNCT = re.compile(r"^[\s.,;:!?\-–—]+|[\s.,;:!?\-–—]+$")
_LEADING_VERBS = re.compile(
    r"^(?:explain|define|describe|discuss|write|what is|what are|what do you mean by)\s+",
    re.I,
)
_LEADING_ARTICLE = re.compile(r"^(?:the|a|an)\s+", re.I)
_ADVANTAGES_PREFIX = re.compile(r"^(?:advantages|disadvantages|features|applications)\s+of\s+", re.I)
_WORKING_OF_PREFIX = re.compile(r"^working\s+of\s+", re.I)
_DIFFERENCE_PREFIX = re.compile(r"^difference\s+between\s+", re.I)
_TRAILING_BOILERPLATE = re.compile(
    r"\s+(?:with\s+)?(?:suitable\s+)?(?:diagram|figure|examples?|briefly|in detail|"
    r"properly|clearly|neatly|accurately)(?:\s+.*)?$",
    re.I,
)
_TRAILING_MARKS_PHRASE = re.compile(r"\s+\[?\d+\s*(?:marks?|m)\]?.*$", re.I)


def _clean_topic_phrase(phrase: str) -> str:
    phrase = _normalize_phrase(phrase)
    phrase = _LEADING_VERBS.sub("", phrase)
    phrase = _LEADING_ARTICLE.sub("", phrase)
    phrase = _ADVANTAGES_PREFIX.sub("", phrase)
    phrase = _WORKING_OF_PREFIX.sub("", phrase)
    phrase = _DIFFERENCE_PREFIX.sub("", phrase)
    phrase = _TRAILING_BOILERPLATE.sub("", phrase)
    phrase = _TRAILING_MARKS_PHRASE.sub("", phrase)
    phrase = _MARKS_SUFFIX.sub("", phrase)
    return _normalize_phrase(phrase)


def _normalize_phrase(phrase: str) -> str:
    phrase = _TRAILING_PUNCT.sub("", phrase.strip())
    phrase = re.sub(r"\s+", " ", phrase)
    return phrase.strip()


def _is_metadata(phrase: str) -> bool:
    if not phrase:
        return True
    for pattern in _METADATA_PATTERNS:
        if pattern.match(phrase.strip()):
            return True
    return False


def is_valid_topic(phrase: str) -> bool:
    """Return True if phrase looks like a real academic topic, not boilerplate."""
    phrase = _clean_topic_phrase(phrase)
    if not phrase or len(phrase) < 3:
        return False
    if _is_metadata(phrase):
        return False

    lower = phrase.lower()
    words = lower.split()

    # Reject sentence-like phrases — real syllabus topics are short noun phrases,
    # not whole questions that slipped past the instruction-verb stripping.
    if len(words) > 8 or len(phrase) > 80:
        return False

    # Reject phrases that dangle on a connector word (e.g. "types of",
    # "difference between", "working of") — these lost their actual topic.
    _DANGLING = {
        "and", "or", "of", "in", "on", "for", "with", "to", "by", "the", "a",
        "an", "between", "from", "into", "about", "vs", "versus",
    }
    if words and (words[0] in _DANGLING or words[-1] in _DANGLING):
        return False

    # Reject if every word is a stopword
    if all(w in EXAM_STOPWORDS for w in words):
        return False

    # Reject if phrase is only instruction verbs
    if lower in EXAM_STOPWORDS:
        return False

    # Reject single instruction words explicitly
    instruction_only = {
        "explain", "describe", "write", "discuss", "state", "define", "list",
        "mention", "compare", "differentiate", "advantages", "disadvantages",
        "features", "functions", "importance", "applications", "uses",
        "what", "why", "how", "when", "where", "which", "short", "note", "notes",
        "a", "an", "the",
    }
    if lower in instruction_only:
        return False

    # Single-word topics: must be technical-looking (acronym, long, or hyphenated)
    if len(words) == 1:
        word = words[0]
        # Use the original (un-lowercased) phrase to detect acronyms reliably.
        original = phrase.split()[0] if phrase.split() else phrase
        if word in EXAM_STOPWORDS:
            return False
        if word.isdigit():
            return False
        if original.isupper() and len(original) >= 2:  # CPU, SQL, HTML, TCP, UDP
            return True
        if "-" in word and len(word) >= 5:
            return True
        if len(word) < 5:
            return False
        # Reject common short verbs/adjectives
        if word.endswith(("ing", "ed", "ly", "er", "or")) and len(word) < 8:
            return False

    # Multi-word: at least one substantive word (not all stopwords)
    substantive = [w for w in words if w not in EXAM_STOPWORDS and len(w) >= 3]
    if not substantive:
        return False

    # Reject phrases that are mostly generic
    generic_ratio = sum(1 for w in words if w in EXAM_STOPWORDS) / len(words)
    if generic_ratio > 0.6:
        return False

    return True


def _title_case_topic(phrase: str) -> str:
    phrase = _clean_topic_phrase(phrase)
    if phrase.isupper() and len(phrase) <= 6:
        return phrase  # keep acronyms
    # Preserve known acronyms inside phrase
    parts = phrase.split()
    result = []
    for part in parts:
        if part.isupper() and len(part) >= 2:
            result.append(part)
        else:
            result.append(part.capitalize())
    return " ".join(result)


def _extract_from_question_line(line: str) -> list[str]:
    line = _QUESTION_PREFIX.sub("", line).strip()
    line = _MARKS_SUFFIX.sub("", line).strip()
    if len(line) < 8:
        return []

    candidates: list[str] = []

    # Take substantive segments after instruction verbs
    segments = _INSTRUCTION_SPLIT.split(line)
    for segment in segments:
        segment = _clean_topic_phrase(segment)
        if is_valid_topic(segment):
            candidates.append(segment)

    # "difference between X and Y"
    between_match = re.search(
        r"(?:difference|differences|compare|contrast|distinguish|differentiate)"
        r"(?:\s+between)?\s+(.+?)\s+and\s+(.+?)(?:\.|\[|$)",
        line,
        re.I,
    )
    if between_match:
        for group in between_match.groups():
            phrase = _clean_topic_phrase(group)
            if is_valid_topic(phrase):
                candidates.append(phrase)

    # "notes on X" / "on X"
    for match in re.finditer(
        r"(?:notes?\s+on|based\s+on|concept\s+of|principle\s+of|types?\s+of|"
        r"working\s+of|algorithm\s+for|detection\s+of|recovery\s+in)\s+"
        r"([A-Za-z][A-Za-z0-9\s\-/,]{2,50}?)(?:\s+and\s+([A-Za-z][A-Za-z0-9\s\-/,]{2,40}))?(?:\.|\[|$)",
        line,
        re.I,
    ):
        for group in match.groups():
            if group:
                phrase = _clean_topic_phrase(group)
                if is_valid_topic(phrase):
                    candidates.append(phrase)

    # Fallback preposition capture (tighter than before)
    for match in re.finditer(
        r"(?:between|of|on|about|regarding|in|for)\s+"
        r"([A-Za-z][A-Za-z0-9\s\-/,]{3,50}?)(?:\s+and\s+([A-Za-z][A-Za-z0-9\s\-/,]{2,40}))?(?:\.|\[|$)",
        line,
        re.I,
    ):
        for group in match.groups():
            if group:
                phrase = _clean_topic_phrase(group)
                if is_valid_topic(phrase):
                    candidates.append(phrase)

    return candidates


def _extract_capitalized_phrases(text: str) -> list[str]:
    """Extract multi-word capitalized terms (e.g. Binary Search Tree)."""
    found: list[str] = []
    for match in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text):
        phrase = match.group(1)
        if is_valid_topic(phrase):
            found.append(phrase)
    return found


def _extract_acronyms(text: str) -> list[str]:
    return [
        m.group(0)
        for m in re.finditer(r"\b[A-Z]{2,6}\b", text)
        if m.group(0) not in {"THE", "AND", "FOR", "NOT", "BUT", "ARE", "WAS", "HAS"}
    ]


def extract_topics(content: str, question_lines: list[str] | None = None) -> tuple[dict[str, int], list[dict]]:
    """
    Extract meaningful topics from PYQ content.
    Returns (topic_frequency dict, important_topics list).
    """
    lines = question_lines or []
    if not lines:
        lines = [ln.strip() for ln in content.splitlines() if len(ln.strip()) > 15]

    counter: Counter[str] = Counter()

    for line in lines:
        for phrase in _extract_from_question_line(line):
            cleaned = _clean_topic_phrase(phrase)
            if cleaned:
                counter[cleaned.lower()] += 1

    for phrase in _extract_capitalized_phrases(content):
        counter[phrase.lower()] += 2  # boost proper nouns / technical terms

    for acronym in _extract_acronyms(content):
        counter[acronym.lower()] += 1

    # Fallback: hyphenated / technical single terms from question lines only
    if len(counter) < 5:
        question_text = " ".join(lines)
        for match in re.finditer(r"\b([a-z]{5,}(?:-[a-z]{3,})+)\b", question_text, re.I):
            term = match.group(1).lower()
            if term not in EXAM_STOPWORDS and is_valid_topic(term):
                counter[term] += 1

    # Build ranked topics, preserving display casing
    display_names: dict[str, str] = {}
    for phrase, _ in counter.items():
        display_names[phrase] = _title_case_topic(phrase)

    ranked = [
        (phrase, count)
        for phrase, count in counter.most_common(50)
        if is_valid_topic(phrase)
    ]

    if not ranked:
        return {}, []

    max_count = ranked[0][1]
    topic_frequency = {display_names[p]: c for p, c in ranked[:20]}
    important_topics = [
        {
            "topic": display_names[phrase],
            "score": round(count / max_count, 2),
            "reason": f"Appears in {count} question(s)",
        }
        for phrase, count in ranked[:12]
    ]

    return topic_frequency, important_topics


def filter_topics(topics: list[str]) -> list[str]:
    """Remove invalid/boilerplate topics from a list."""
    seen: set[str] = set()
    result: list[str] = []
    for topic in topics:
        normalized = topic.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        if is_valid_topic(normalized):
            seen.add(key)
            result.append(_title_case_topic(normalized))
    return result


from app.utils.syllabus_units import assign_syllabus_unit


def _importance_for_frequency(freq: int) -> str:
    if freq >= 3:
        return "High"
    if freq == 2:
        return "Medium"
    return "Low"


def _clean_frequency_row(row: dict) -> dict | None:
    topic = str(row.get("topic", ""))
    if not is_valid_topic(topic):
        return None
    freq = int(row.get("frequency", 0))
    return {
        "topic": _title_case_topic(topic),
        "unit": str(row.get("unit") or assign_syllabus_unit(topic)),
        "frequency": freq,
    }


def sanitize_analysis_result(result: dict[str, Any]) -> dict[str, Any]:
    """Clean topic fields in an analysis result dict."""
    important = result.get("important_topics") or []
    cleaned_important = []
    for item in important:
        topic = item.get("topic", "")
        if is_valid_topic(topic):
            cleaned_important.append({**item, "topic": _title_case_topic(topic)})

    raw_freq = result.get("topic_frequency") or {}
    cleaned_freq: dict[str, int] = {}
    for topic, count in raw_freq.items():
        if is_valid_topic(str(topic)):
            cleaned_freq[_title_case_topic(str(topic))] = int(count)

    result["important_topics"] = cleaned_important[:20]
    result["topic_frequency"] = dict(
        sorted(cleaned_freq.items(), key=lambda x: x[1], reverse=True)
    )
    result["repeated_questions"] = []

    def _clean_table(rows: list) -> list[dict]:
        cleaned = []
        for row in rows or []:
            topic = str(row.get("topic", ""))
            if not is_valid_topic(topic):
                continue
            freq = int(row.get("frequency", 0))
            cleaned.append({
                "topic": _title_case_topic(topic),
                "frequency": freq,
                "importance": str(row.get("importance") or _importance_for_frequency(freq)),
            })
        return cleaned

    if result.get("topic_table"):
        result["topic_table"] = _clean_table(result["topic_table"])
    elif cleaned_freq:
        result["topic_table"] = [
            {
                "topic": t,
                "frequency": f,
                "importance": _importance_for_frequency(f),
            }
            for t, f in sorted(cleaned_freq.items(), key=lambda x: -x[1])
        ]

    table = result.get("topic_table", [])

    # Topic frequency table with unit
    if result.get("topic_frequency_table"):
        freq_table = [
            row for row in (_clean_frequency_row(r) for r in result["topic_frequency_table"]) if row
        ]
    elif table:
        freq_table = [
            {
                "topic": r["topic"],
                "unit": assign_syllabus_unit(r["topic"]),
                "frequency": r["frequency"],
            }
            for r in table
        ]
    else:
        freq_table = []

    result["topic_frequency_table"] = freq_table

    high_priority = [r for r in freq_table if r["frequency"] >= 3]
    medium_priority = [r for r in freq_table if r["frequency"] == 2]
    low_priority = [r for r in freq_table if r["frequency"] == 1]
    predicted = sorted(high_priority + medium_priority, key=lambda x: -x["frequency"])

    result["high_priority_topics"] = high_priority
    result["medium_priority_topics"] = medium_priority
    result["low_priority_topics"] = low_priority
    result["predicted_important_topics"] = predicted
    result["most_important_topics"] = high_priority
    result["frequently_asked_topics"] = high_priority + medium_priority
    result["rarely_asked_topics"] = low_priority

    if not result.get("syllabus_topics") and freq_table:
        result["syllabus_topics"] = [r["topic"] for r in freq_table]

    if result.get("academic_topic_table"):
        result["academic_topic_table"] = [
            {"topic": r["topic"], "frequency": int(r["frequency"])}
            for r in _clean_table(result["academic_topic_table"])
        ]
    elif freq_table:
        result["academic_topic_table"] = [
            {"topic": r["topic"], "frequency": r["frequency"]} for r in freq_table
        ]

    return result
