#!/usr/bin/env python3
"""Validate ExamBuddy exam notes (v19) rendering."""

from app.services.ai.notes_structured import (
    is_structured_notes_result,
    structured_notes_to_markdown,
)
from app.services.notes_engine.markdown_formatter import format_exam_notes_markdown
from app.services.notes_engine.schema import PROMPT_VERSION
from app.services.notes_engine.validator import deduplicate_structured_notes, validate_exam_notes

SAMPLE = {
    "topic": "Virtual Memory",
    "topicType": "Operating System",
    "definition": "Virtual memory lets a computer run programs larger than physical RAM by using disk as an extension of main memory.",
    "introduction": "It solves the limited-RAM problem so multiprogramming stays practical.",
    "detailedExplanation": "CPU uses virtual addresses. MMU translates via page tables. Missing pages cause page faults loaded from disk.",
    "keyConcepts": ["**Paging** — fixed-size blocks", "**Page fault** — missing page interrupt"],
    "working": "1. CPU issues virtual address\n2. MMU looks up page table\n3. On miss, page fault loads from disk",
    "diagram": "flowchart TD\nCPU --> MMU\nMMU --> RAM\nMMU --> Disk",
    "example": "A 4 GB program on 2 GB RAM keeps only needed pages in RAM.",
    "advantages": ["Run larger programs"],
    "disadvantages": ["Thrashing under heavy faults"],
    "applications": ["Multiprogramming OS memory management"],
    "frequentlyAskedQuestions": [
        {"question": "What is virtual memory?", "answer": "Technique to use disk as extension of RAM."}
    ],
    "twoMarkAnswer": "Virtual memory extends RAM using disk via paging.",
    "fiveMarkAnswer": "Define VM, explain paging + page fault, give one advantage.",
    "tenMarkAnswer": "Definition, need, address translation, page fault handling, diagram, thrashing, comparison with contiguous allocation.",
    "vivaQuestions": [
        {"question": "Define page fault.", "answer": "Interrupt when required page is not in memory."}
    ],
    "interviewQuestions": [
        {"question": "What is thrashing?", "answer": "Too many page faults; system spends time swapping."}
    ],
    "commonMistakes": ["Confusing paging with segmentation"],
    "revisionSummary": [
        "VM extends RAM using disk",
        "Paging + page tables",
        "Page fault on miss",
    ],
    "keywords": ["virtual memory", "paging", "page fault", "MMU"],
    "comparison": {
        "title": "Paging vs Segmentation",
        "headers": ["Aspect", "Paging", "Segmentation"],
        "rows": [["Unit", "Fixed-size pages", "Variable-size segments"]],
    },
}


def main() -> None:
    assert PROMPT_VERSION.startswith("v19")
    assert is_structured_notes_result(SAMPLE)
    md = structured_notes_to_markdown(SAMPLE)
    assert "# Virtual Memory" in md
    assert "## Definition" in md
    assert "## Working" in md
    assert "## 2-Mark Answer" in md
    assert "## 10-Mark Answer" in md
    assert "## Revision Summary" in md
    assert "## Viva Questions" in md
    assert "```mermaid" in md
    validate_exam_notes(SAMPLE, markdown=md)

    deduped = deduplicate_structured_notes(
        {
            **SAMPLE,
            "revisionSummary": [
                "VM extends RAM using disk",
                "VM extends RAM using disk",
                "Paging + page tables",
            ],
        }
    )
    assert len(deduped["revisionSummary"]) == 2

    legacy_md = format_exam_notes_markdown(
        {
            "topic": "HTTP",
            "whatIsIt": "HTTP is a request-response protocol for the web.",
            "whyNeeded": "Browsers need a shared language to talk to servers.",
            "revisionSheet": ["Client request", "Server response"],
            "vivaQuestions": [{"question": "What is HTTP?", "answer": "HyperText Transfer Protocol."}],
        }
    )
    assert "## Definition" in legacy_md

    print("ExamBuddy v19 structured notes checks passed.")
    print(md[:700].encode("ascii", "replace").decode("ascii"), "...")


if __name__ == "__main__":
    main()
