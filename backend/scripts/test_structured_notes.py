#!/usr/bin/env python3
"""Validate structured notes JSON rendering."""

from app.services.ai.notes_structured import (
    is_structured_notes_result,
    structured_notes_to_markdown,
)

SAMPLE = {
    "topic": "Virtual Memory",
    "definition": "Virtual memory is a memory management technique.",
    "introduction": "It allows programs to use more memory than physical RAM.",
    "working": "1. CPU generates address\n2. MMU translates\n3. Page fault if missing",
    "components": ["Page table", "MMU", "Swap space"],
    "advantages": ["Larger address space", "Process isolation"],
    "disadvantages": ["Page fault overhead"],
    "applications": ["Multitasking operating systems"],
    "example": "A 4 GB program on 2 GB RAM using paging.",
    "comparison": {
        "left": "Paging",
        "compareWith": "Segmentation",
        "table": [
            {
                "aspect": "Unit",
                "leftValue": "Fixed-size pages",
                "rightValue": "Variable-size segments",
            }
        ],
    },
    "interviewQuestions": [
        {"question": "What is virtual memory?", "answer": "A technique to use disk as extension of RAM."}
    ],
    "vivaQuestions": [
        {"question": "Define page fault.", "answer": "Interrupt when required page is not in memory."}
    ],
    "examTips": ["Draw page table diagram", "Mention thrashing"],
    "keywords": ["paging", "MMU", "page fault"],
    "summary": "Virtual memory extends RAM using disk with paging and page tables.",
}


def main() -> None:
    assert is_structured_notes_result(SAMPLE)
    md = structured_notes_to_markdown(SAMPLE)
    assert "# Virtual Memory" in md
    assert "## Definition" in md
    assert "## Interview Questions" in md
    assert "### Q1." in md
    assert "## Comparison" in md
    assert "Paging" in md
    assert "Segmentation" in md
    assert "⭐" not in md
    print("Structured notes renderer checks passed.")
    print(md[:600], "...")


if __name__ == "__main__":
    main()
