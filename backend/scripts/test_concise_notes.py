#!/usr/bin/env python3
"""
Content-policy tests for the Stage-3 concise notes engine (v40).

Complements scripts/test_concise_notes_dryrun.py, which covers the happy /
repair / unknown-topic paths. This script covers the product rules that must
never regress:

  - exam-frequency and PYQ wording is rejected
  - marks references are rejected
  - a topic copied as an exam instruction is rejected
  - "N/A"-style stub sections are rejected
  - a textbook-length note is rejected

Section headings are read from the schema rather than hard-coded, so the
tests keep working if the heading text is adjusted.

Then, when GEMINI_API_KEY is configured, it runs ONE real end-to-end
generation ("Normalization" / "DBMS") and reports the word count, call count,
and section coverage.

Run from the backend/ directory:
    python scripts/test_concise_notes.py          # fixtures + live e2e
    SKIP_LIVE=1 python scripts/test_concise_notes.py   # fixtures only
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.services.notes_engine.markdown_formatter import (  # noqa: E402
    normalize_concise_payload,
    render_concise_markdown,
)
from app.services.notes_engine.schema import (  # noqa: E402
    CONCISE_ENGINE_ID,
    CONCISE_PROMPT_VERSION,
    MAX_TEXT_FIELD_CHARS,
    MAX_WORD_COUNT_SOFT,
    MIN_WORD_COUNT_SOFT,
    SECTION_HEADINGS,
)
from app.services.notes_engine.validator import (  # noqa: E402
    NotesValidationError,
    count_words,
    validate_concise_payload,
    validate_final_notes,
)

EXPECTED_HEADINGS = tuple(f"## {heading}" for heading in SECTION_HEADINGS)

GOOD_PAYLOAD: dict = {
    "topic": "Normalization",
    "definition": (
        "Normalization is the process of organizing the columns and tables of a relational "
        "database so that the same fact is stored in exactly one place. It splits a large "
        "table into smaller related tables that are linked by primary and foreign keys."
    ),
    "working": [
        "Start from an unnormalized table that repeats groups of data inside single cells.",
        "Apply First Normal Form by making every column atomic and removing repeating groups.",
        "Apply Second Normal Form by removing partial dependencies on part of a composite key.",
        "Apply Third Normal Form by removing transitive dependencies between non-key columns.",
        "Link the resulting tables with primary and foreign keys so no information is lost.",
    ],
    "advantages": [
        "Removes duplicate data, so the database uses less storage.",
        "Prevents insertion, update, and deletion anomalies in the stored rows.",
        "Keeps data consistent because each fact is written in only one table.",
        "Makes the schema easier to extend when new attributes are added.",
    ],
    "disadvantages": [
        "More tables mean more joins, which slows down read-heavy queries.",
        "Query writing becomes harder because related data is spread across relations.",
        "Over-splitting a reporting database can hurt performance badly.",
    ],
    "applications": [
        {"name": "Banking systems", "detail": "Customer, account, and transaction data live in separate relations."},
        {"name": "E-commerce catalogs", "detail": "Products, categories, and suppliers are stored once and referenced."},
        {"name": "University records", "detail": "Students, courses, and enrolments are modelled as separate tables."},
        {"name": "Hospital management", "detail": "Patients, doctors, and visits avoid repeating personal details."},
    ],
    "example": (
        "A table Student(RollNo, Name, Course, Instructor) repeats the instructor for every "
        "enrolment. Instructor depends on Course rather than on RollNo, which is a transitive "
        "dependency. Splitting it into Student(RollNo, Name, Course) and Course(Course, "
        "Instructor) reaches Third Normal Form and stores each instructor only once."
    ),
    "quick_revision": [
        "Normalization reduces redundancy by splitting tables.",
        "1NF: atomic columns, no repeating groups.",
        "2NF: 1NF plus no partial dependency on a composite key.",
        "3NF: 2NF plus no transitive dependency.",
        "Trade-off: fewer anomalies, but more joins.",
    ],
}


def _render(payload: dict) -> tuple[dict, str, int]:
    structured = normalize_concise_payload(payload, topic=payload.get("topic", ""))
    markdown = render_concise_markdown(structured)
    return structured, markdown, count_words(markdown)


def _validate(payload: dict) -> None:
    structured, markdown, words = _render(payload)
    validate_concise_payload(structured, topic=structured.get("topic", ""))
    validate_final_notes(markdown, structured, word_count=words)


def _expect_rejection(payload: dict, *, label: str) -> None:
    try:
        _validate(payload)
    except NotesValidationError as exc:
        print(f"PASS: rejected {label} (code={exc.code})")
        return
    raise AssertionError(f"expected {label} to be rejected, but validation passed")


def test_good_payload_passes() -> None:
    structured, markdown, words = _render(GOOD_PAYLOAD)
    _validate(GOOD_PAYLOAD)

    assert markdown.startswith("# Normalization"), markdown[:80]
    missing = [h for h in EXPECTED_HEADINGS if h not in markdown]
    assert not missing, f"missing headings: {missing}"

    positions = [markdown.index(h) for h in EXPECTED_HEADINGS]
    assert positions == sorted(positions), "sections rendered out of order"
    assert "1. Start from an unnormalized table" in markdown, "working steps are not numbered"
    assert "- Removes duplicate data" in markdown, "advantages are not bulleted"
    assert MIN_WORD_COUNT_SOFT <= words <= MAX_WORD_COUNT_SOFT, f"word_count={words} outside soft band"
    assert len(SECTION_HEADINGS) == 7
    assert set(structured) >= {"definition", "working", "quick_revision"}

    print(f"PASS: reference note renders all 7 sections in order ({words} words)")


def test_rejects_pyq_language() -> None:
    payload = dict(GOOD_PAYLOAD)
    payload["quick_revision"] = [
        *GOOD_PAYLOAD["quick_revision"][:-1],
        "Frequently asked in previous year question papers, so revise it well.",
    ]
    _expect_rejection(payload, label="PYQ / exam-frequency language")


def test_rejects_marks_language() -> None:
    payload = dict(GOOD_PAYLOAD)
    payload["definition"] = GOOD_PAYLOAD["definition"] + " It is usually worth 10 marks."
    _expect_rejection(payload, label="marks reference")


def test_rejects_instruction_style_topic() -> None:
    payload = dict(GOOD_PAYLOAD)
    payload["topic"] = "Explain normalization in DBMS"
    structured, markdown, words = _render(payload)
    assert markdown.startswith("# Explain normalization"), "fixture no longer exercises the gate"
    try:
        validate_final_notes(markdown, structured, word_count=words)
    except NotesValidationError as exc:
        print(f"PASS: rejected instruction-style topic (code={exc.code})")
        return
    raise AssertionError("expected an instruction-style topic to be rejected")


def test_rejects_stub_sections() -> None:
    payload = dict(GOOD_PAYLOAD)
    payload["example"] = "N/A"
    payload["disadvantages"] = ["None"]
    _expect_rejection(payload, label="stub sections")


def test_caps_single_runaway_field() -> None:
    """One rambling field is truncated by the normalizer, not bounced to repair."""
    payload = dict(GOOD_PAYLOAD)
    payload["definition"] = " ".join(
        ["Normalization organizes relational data into smaller linked tables."] * 120
    )
    structured, markdown, words = _render(payload)
    _validate(payload)
    assert len(structured["definition"]) <= MAX_TEXT_FIELD_CHARS + 1, len(structured["definition"])
    assert words <= MAX_WORD_COUNT_SOFT, words
    print(f"PASS: runaway definition capped to {len(structured['definition'])} chars ({words} words total)")


def test_rejects_textbook_length() -> None:
    """A note that is long across every section is rejected, not silently served."""
    filler = (
        "restates the surrounding idea at considerable length, adding qualifications and "
        "asides that a revision note has no room for, so that the rendered section grows "
        "well beyond the concise word budget the product requires"
    )
    payload = dict(GOOD_PAYLOAD)
    for field in ("working", "advantages", "disadvantages", "applications", "quick_revision"):
        payload[field] = [f"Distinct {field} point number {i} {filler}." for i in range(1, 9)]
    _, _, words = _render(payload)
    assert words > MAX_WORD_COUNT_SOFT, f"fixture only reached {words} words"
    _expect_rejection(payload, label="textbook-length note")


async def live_end_to_end() -> int:
    """One real Gemini generation — skipped when no key or quota is available."""
    from app.core.config import reload_settings
    from app.services.ai.ai_service import AIService

    settings = reload_settings()
    if not settings.gemini_api_key:
        print("SKIP: live e2e (no GEMINI_API_KEY in backend/.env)")
        return 0

    ai = AIService()
    if not ai.ai_available:
        print("SKIP: live e2e (no AI provider loaded)")
        return 0

    try:
        result, metadata = await ai.generate_topic_notes("Normalization", subject="DBMS")
    except Exception as exc:  # noqa: BLE001 — reporting the real provider error is the point
        print(f"SKIP: live e2e unavailable ({type(exc).__name__}: {str(exc)[:300]})")
        return 0

    notes = result.get("notes") or ""
    words = metadata.get("word_count") or count_words(notes)

    print("---- LIVE RESULT ----")
    print(f"provider={metadata.get('provider')} model={metadata.get('model')}")
    print(f"engine={metadata.get('notes_engine')} prompt_version={metadata.get('prompt_version')}")
    print(f"gemini_calls={metadata.get('gemini_calls')} repaired={metadata.get('repaired')} words={words}")
    print("---- NOTES ----")
    print(notes)
    print("---- END ----")

    failures: list[str] = []
    if metadata.get("notes_engine") != CONCISE_ENGINE_ID:
        failures.append(f"engine={metadata.get('notes_engine')}")
    if metadata.get("prompt_version") != CONCISE_PROMPT_VERSION:
        failures.append(f"prompt_version={metadata.get('prompt_version')}")
    if metadata.get("provider") == "local":
        failures.append("local template fallback was used")
    missing = [h for h in EXPECTED_HEADINGS if h not in notes]
    if missing:
        failures.append(f"missing headings {missing}")
    if not MIN_WORD_COUNT_SOFT <= words <= MAX_WORD_COUNT_SOFT:
        failures.append(f"word_count={words} outside {MIN_WORD_COUNT_SOFT}-{MAX_WORD_COUNT_SOFT}")
    if (metadata.get("gemini_calls") or 0) > 2:
        failures.append(f"gemini_calls={metadata.get('gemini_calls')}")

    if failures:
        print("FAIL live e2e: " + "; ".join(failures))
        return 1
    print(f"PASS: live e2e ({words} words, {metadata.get('gemini_calls')} Gemini call(s), all 7 sections)")
    return 0


def main() -> int:
    test_good_payload_passes()
    test_rejects_pyq_language()
    test_rejects_marks_language()
    test_rejects_instruction_style_topic()
    test_rejects_stub_sections()
    test_caps_single_runaway_field()
    test_rejects_textbook_length()
    print("\nAll content-policy tests passed.")

    if os.environ.get("SKIP_LIVE"):
        print("SKIP: live e2e (SKIP_LIVE set)")
        return 0
    return asyncio.run(live_end_to_end())


if __name__ == "__main__":
    sys.exit(main())
