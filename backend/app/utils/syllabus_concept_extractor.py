"""
Academic syllabus concept extraction from exam questions.
Extracts ONLY concepts students must study — never verbs or instructions.
"""

from __future__ import annotations

import re
from collections import Counter

from app.utils.topic_extractor import (
    _clean_topic_phrase,
    _title_case_topic,
    is_valid_topic,
)

INSTRUCTION_WORDS = {
    "explain", "describe", "write", "discuss", "state", "define", "list", "mention",
    "compare", "differentiate", "distinguish", "enumerate", "illustrate", "outline",
    "summarize", "summarise", "highlight", "elaborate", "analyse", "analyze", "examine",
    "justify", "derive", "calculate", "compute", "solve", "sketch", "draw", "prove",
    "name", "identify", "comment", "bring", "briefly", "short", "note", "notes",
    "advantages", "disadvantages", "features", "functions", "importance", "applications",
    "uses", "what", "why", "how", "when", "where", "which", "whose", "whom", "whether",
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for", "with", "by",
    "from", "into", "about", "regarding", "between", "among", "through", "during",
    "is", "are", "was", "were", "be", "been", "being", "has", "have", "had", "do",
    "does", "did", "will", "would", "could", "should", "shall", "may", "might", "must",
    "not", "no", "yes", "true", "false", "given", "following", "below", "above",
    "marks", "mark", "question", "answer", "section", "paper", "attempt", "total",
    "diagram", "figure", "example", "examples", "suitable", "properly", "clearly",
    "account", "reason", "help", "using", "respect", "terms", "meaning", "means",
    "difference", "differences", "contrast", "similarities", "types", "type",
    "working", "principle", "concept", "brief", "detailed", "neat", "accurate",
}

# Action verbs that signal a new instruction has begun mid-phrase. When one of
# these appears after the first word, the real topic ended before it.
HARD_INSTRUCTION_VERBS = {
    "explain", "describe", "write", "discuss", "state", "define", "list",
    "mention", "compare", "differentiate", "distinguish", "enumerate",
    "illustrate", "outline", "summarize", "summarise", "elaborate", "analyse",
    "analyze", "examine", "justify", "derive", "calculate", "compute", "solve",
    "sketch", "draw", "prove", "identify",
}

_QUESTION_PREFIX = re.compile(
    r"^(?:\d+[\).\]]|\([a-z]\)|[Qq]\d+[\).:]|[ivxIVX]+[\).\]])\s*",
    re.I,
)
_MARKS_SUFFIX = re.compile(r"\[?\s*\d+\s*(?:marks?|m)\s*\]?\s*$", re.I)
_TRAILING_JUNK = re.compile(
    r"\s+(?:with\s+)?(?:an?\s+)?(?:suitable\s+)?(?:diagram|figure|examples?|briefly|"
    r"in detail|neatly|clearly|properly)(?:\s+.*)?$",
    re.I,
)

# Standardized syllabus topic names
STANDARDIZED_TOPICS: dict[str, str] = {
    "cloud computing": "Cloud Computing",
    "tcp/ip architecture": "TCP/IP Architecture",
    "tcp/ip": "TCP/IP",
    "tcpip": "TCP/IP",
    "tcp ip architecture": "TCP/IP Architecture",
    "normalization": "Database Normalization",
    "database normalization": "Database Normalization",
    "primary key": "Database Keys",
    "foreign key": "Database Keys",
    "primary key and foreign key": "Database Keys",
    "foreign key and primary key": "Database Keys",
    "http": "HTTP Protocol",
    "https": "HTTPS Protocol",
    "http protocol": "HTTP Protocol",
    "https protocol": "HTTPS Protocol",
    "deadlock": "Deadlock",
    "operating system": "Operating System",
    "binary search tree": "Binary Search Tree",
    "avl tree": "AVL Tree",
    "stack": "Stack",
    "queue": "Queue",
    "linked list": "Linked List",
    "polymorphism": "Polymorphism",
    "inheritance": "Inheritance",
    "encapsulation": "Encapsulation",
    "dijkstra algorithm": "Dijkstra Algorithm",
    "object oriented programming": "Object Oriented Programming",
    "oop": "Object Oriented Programming",
    "sql": "SQL",
    "dbms": "Database Management System",
    # Networking
    "osi model": "OSI Model",
    "osi reference model": "OSI Model",
    "subnetting": "Subnetting",
    "routing algorithm": "Routing Algorithms",
    "routing algorithms": "Routing Algorithms",
    "congestion control": "Congestion Control",
    "flow control": "Flow Control",
    "error detection": "Error Detection",
    "error control": "Error Control",
    "ip address": "IP Addressing",
    "ip addressing": "IP Addressing",
    "dns": "DNS",
    "domain name system": "DNS",
    # DBMS
    "er diagram": "ER Model",
    "entity relationship diagram": "ER Model",
    "er model": "ER Model",
    "transaction": "Transaction Management",
    "transaction management": "Transaction Management",
    "concurrency control": "Concurrency Control",
    "acid properties": "ACID Properties",
    "relational algebra": "Relational Algebra",
    "indexing": "Indexing",
    "functional dependency": "Functional Dependency",
    # Operating Systems
    "process scheduling": "Process Scheduling",
    "cpu scheduling": "CPU Scheduling",
    "page replacement": "Page Replacement",
    "paging": "Paging",
    "segmentation": "Segmentation",
    "virtual memory": "Virtual Memory",
    "semaphore": "Semaphores",
    "semaphores": "Semaphores",
    "memory management": "Memory Management",
    "process synchronization": "Process Synchronization",
    # Data structures / algorithms
    "hashing": "Hashing",
    "graph": "Graphs",
    "graphs": "Graphs",
    "tree traversal": "Tree Traversal",
    "sorting algorithm": "Sorting Algorithms",
    "sorting algorithms": "Sorting Algorithms",
    "searching algorithm": "Searching Algorithms",
    "dynamic programming": "Dynamic Programming",
    "greedy algorithm": "Greedy Algorithms",
    "recursion": "Recursion",
    # OOP / Java
    "abstraction": "Abstraction",
    "exception handling": "Exception Handling",
    "multithreading": "Multithreading",
    "interface": "Interfaces",
    "constructor": "Constructors",
}

_CONCEPT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:advantages|disadvantages|features|functions|importance|applications|uses)"
        r"(?:\s+and\s+(?:dis)?advantages)?\s+of\s+(?:the\s+)?(.+?)(?:\.|\[|\?|$)",
        re.I,
    ),
    re.compile(r"(?:short\s+)?notes?\s+on\s+(.+?)(?:\.|\[|\?|$)", re.I),
    re.compile(r"what\s+(?:is|are)\s+(.+?)(?:\?|\.|\[|$)", re.I),
    re.compile(
        r"(?:explain|describe|discuss|define|state|list|mention|write|illustrate)"
        r"(?:\s+briefly)?\s+(?:the\s+)?(?:concept\s+of\s+)?(.+?)(?:\.|\[|\?|$)",
        re.I,
    ),
    re.compile(
        r"(?:compare|contrast|differentiate|distinguish)(?:\s+between)?\s+"
        r"(.+?)\s+and\s+(.+?)(?:\.|\[|\?|$)",
        re.I,
    ),
    re.compile(
        r"(?:architecture|algorithm|detection|recovery|implementation)\s+"
        r"(?:of|for|in)\s+(.+?)(?:\.|\[|\?|$)",
        re.I,
    ),
    re.compile(r"working\s+of\s+(.+?)(?:\.|\[|\?|$)", re.I),
]

_TRAILING_CONTEXT = re.compile(
    r"\s+in\s+(?:dbms|database(?:\s+management\s+system)?|operating\s+system|os|"
    r"computer\s+networks?|java|python|c\+\+)$",
    re.I,
)


def _normalize(phrase: str) -> str:
    return re.sub(r"\s+", " ", phrase.strip())


def _canonical_key(topic: str) -> str:
    key = _clean_topic_phrase(topic).lower()
    key = re.sub(r"[^a-z0-9\s\-/+]", "", key)
    return re.sub(r"\s+", " ", key).strip()


def _standardize_topic(phrase: str) -> str | None:
    """Map extracted phrase to standardized syllabus topic name."""
    concept = _strip_instruction_words(phrase)
    if not concept:
        return None

    key = _canonical_key(concept)

    # Direct standardized mapping
    if key in STANDARDIZED_TOPICS:
        return STANDARDIZED_TOPICS[key]

    # Partial matches for compound topics
    if "primary key" in key and "foreign key" in key:
        return "Database Keys"
    if "normalization" in key:
        return "Database Normalization"
    if "tcp/ip" in key or "tcpip" in key:
        return "TCP/IP Architecture" if "architecture" in key else "TCP/IP"
    if key == "http":
        return "HTTP Protocol"
    if key == "https":
        return "HTTPS Protocol"

    if not is_valid_topic(concept):
        return None
    if _is_instruction_only(key):
        return None

    if re.match(r"^(its|their|this|these|those)\s", key):
        return None

    return _title_case_topic(concept)


def _strip_instruction_words(phrase: str) -> str:
    phrase = _clean_topic_phrase(phrase)
    phrase = _TRAILING_JUNK.sub("", phrase)
    phrase = _TRAILING_CONTEXT.sub("", phrase)
    phrase = _MARKS_SUFFIX.sub("", phrase)

    words = phrase.split()
    while words and words[0].lower() in INSTRUCTION_WORDS:
        words.pop(0)

    # Cut the phrase at the first embedded instruction verb (after the first
    # word): "deadlock and explain deadlock detection" -> "deadlock".
    for idx in range(1, len(words)):
        if words[idx].lower() in HARD_INSTRUCTION_VERBS:
            words = words[:idx]
            break

    while words and words[-1].lower() in INSTRUCTION_WORDS:
        words.pop()

    return _normalize(" ".join(words))


def _is_instruction_only(phrase: str) -> bool:
    words = phrase.lower().split()
    return not words or all(w in INSTRUCTION_WORDS for w in words)


def _standardize_compare_side(side: str) -> str | None:
    side = _strip_instruction_words(side)
    if not side:
        return None
    return _standardize_topic(side)


def extract_concepts_from_question(line: str) -> list[str]:
    line = _QUESTION_PREFIX.sub("", line.strip())
    line = _MARKS_SUFFIX.sub("", line).strip()
    if len(line) < 8:
        return []

    found: list[str] = []

    # Special: primary/foreign keys
    if re.search(r"primary\s+key", line, re.I) and re.search(r"foreign\s+key", line, re.I):
        return ["Database Keys"]

    # Compound: "What is Deadlock? Explain its prevention methods."
    if re.search(r"deadlock", line, re.I):
        found.append("Deadlock")
        if re.search(r"prevent", line, re.I):
            found.append("Deadlock Prevention")

    for pattern in _CONCEPT_PATTERNS:
        for match in pattern.finditer(line):
            groups = [g for g in match.groups() if g]
            if len(groups) == 2:
                for side in groups:
                    concept = _standardize_compare_side(side)
                    if concept:
                        found.append(concept)
            elif groups:
                concept = _standardize_topic(groups[0])
                if concept:
                    found.append(concept)

    if not found:
        concept = _standardize_topic(line)
        if concept:
            found.append(concept)

    seen: set[str] = set()
    unique: list[str] = []
    for c in found:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def extract_concepts_from_questions(lines: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for line in lines:
        for concept in extract_concepts_from_question(line):
            counter[concept] += 1
    return counter
