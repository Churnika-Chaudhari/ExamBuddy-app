#!/usr/bin/env python3
"""Validate structured notes JSON rendering (exam-notes engine)."""

from app.services.ai.notes_structured import (
    is_structured_notes_result,
    structured_notes_to_markdown,
)
from app.services.notes_engine.markdown_formatter import format_exam_notes_markdown
from app.services.notes_engine.validator import deduplicate_structured_notes

SAMPLE = {
    "topic": "Virtual Memory",
    "definition": "Virtual memory is a memory management technique.",
    "whyItMatters": [
        "Allows programs larger than RAM",
        "Supports multiprogramming",
    ],
    "keyConcepts": ["**Paging** — fixed-size blocks", "**Page fault** — missing page interrupt"],
    "detailedExplanation": "- CPU generates virtual address\n- MMU translates via page table\n- Fault loads page from disk",
    "examples": ["A 4 GB program on 2 GB RAM using paging."],
    "memoryTrick": "V-M: Virtual Maps onto Memory frames",
    "importantExamPoints": [
        "⭐⭐⭐ Page table + MMU translation",
        "⭐⭐ Page fault handling",
        "⭐ Thrashing concept",
    ],
    "commonMistakes": ["Confusing paging with segmentation"],
    "table": {
        "title": "Paging vs Segmentation",
        "headers": ["Aspect", "Paging", "Segmentation"],
        "rows": [["Unit", "Fixed-size pages", "Variable-size segments"]],
    },
    "frequentlyAskedQuestions": [
        {"question": "What is virtual memory?", "answer": "Technique to use disk as extension of RAM."}
    ],
    "vivaQuestions": [
        {"question": "Define page fault.", "answer": "Interrupt when required page is not in memory."}
    ],
    "thirtySecondRevision": [
        "Virtual memory extends RAM using disk",
        "Paging + page tables",
        "Page fault on miss",
    ],
}


def main() -> None:
    assert is_structured_notes_result(SAMPLE)
    md = structured_notes_to_markdown(SAMPLE)
    assert "# Virtual Memory" in md
    assert "## Definition" in md
    assert "## Important Exam Points" in md
    assert "## 30 Second Revision" in md
    assert "## Viva Questions" in md
    assert "### Q1." in md
    assert "## Table" in md
    assert "Paging" in md
    assert "Segmentation" in md

    deduped = deduplicate_structured_notes(
        {
            **SAMPLE,
            "thirtySecondRevision": [
                "Virtual memory extends RAM using disk",
                "Virtual memory extends RAM using disk",
                "Paging + page tables",
            ],
        }
    )
    assert len(deduped["thirtySecondRevision"]) == 2

    exam_md = format_exam_notes_markdown(SAMPLE)
    assert "Memory Trick" in exam_md
    print("Structured notes renderer checks passed.")
    print(exam_md[:500].encode("ascii", "replace").decode("ascii"), "...")


if __name__ == "__main__":
    main()
