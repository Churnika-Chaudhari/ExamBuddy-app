#!/usr/bin/env python3
"""Validate Professor Alex (v18) structured notes rendering."""

from app.services.ai.notes_structured import (
    is_structured_notes_result,
    structured_notes_to_markdown,
)
from app.services.notes_engine.markdown_formatter import format_exam_notes_markdown
from app.services.notes_engine.schema import PROMPT_VERSION
from app.services.notes_engine.validator import deduplicate_structured_notes, validate_exam_notes

SAMPLE = {
    "topic": "Virtual Memory",
    "whatIsIt": (
        "Virtual memory is a way for a computer to pretend it has more RAM than it physically does. "
        "It does this by using disk space as an extension of main memory so large programs can still run."
    ),
    "whyNeeded": "Programs can be bigger than RAM; many programs must share limited physical memory safely.",
    "realLifeAnalogy": "Like a small desk (RAM) with a big filing cabinet (disk). You keep only open papers on the desk.",
    "coreConcept": "1. Virtual addresses\n2. Page tables\n3. Page faults\n4. Frames in RAM",
    "howItWorks": "1. CPU uses a virtual address\n2. MMU translates via page table\n3. On miss, page fault loads from disk",
    "architecture": "CPU → MMU/page table → RAM frames; disk backs missing pages.",
    "components": [
        {
            "name": "MMU",
            "purpose": "Translate addresses",
            "responsibility": "Map virtual → physical",
            "interaction": "Uses page tables; signals faults",
            "simpleExplanation": "The address translator",
        }
    ],
    "diagram": "CPU\n |\nVirtual address\n |\nMMU + Page Table\n |\nRAM / Disk",
    "realWorldExample": "A 4 GB program on 2 GB RAM uses paging so only needed pages stay in RAM.",
    "deepDive": "Page tables store frame numbers; TLB caches recent translations to speed lookups.",
    "advantages": ["Run larger programs — because disk extends usable space"],
    "disadvantages": ["Thrashing — too many page faults slow the system"],
    "comparison": {
        "title": "Paging vs Segmentation",
        "headers": ["Aspect", "Paging", "Segmentation"],
        "rows": [["Unit", "Fixed-size pages", "Variable-size segments"]],
    },
    "commonMistakes": ["Confusing paging with segmentation — both divide memory but differently"],
    "vivaQuestions": [
        {"question": "Define page fault.", "answer": "Interrupt when required page is not in memory."}
    ],
    "examQuestions": {
        "longAnswer": [
            {
                "question": "Explain virtual memory with paging.",
                "answer": "Define VM, show address translation, page fault handling, one diagram.",
            }
        ],
        "shortAnswer": [{"question": "What is a page?", "answer": "Fixed-size block of virtual memory."}],
    },
    "mcqs": [
        {
            "question": "What triggers a page fault?",
            "options": ["Hit in TLB", "Page not in RAM", "Cache warm", "Idle CPU"],
            "answer": "B",
            "explanation": "A fault occurs when the needed page is missing from physical memory.",
        }
    ],
    "memoryTricks": ["V-M: Virtual Maps onto Memory frames"],
    "revisionSheet": [
        "VM extends RAM using disk",
        "Paging + page tables",
        "Page fault on miss",
        "TLB speeds translation",
    ],
    "keyTakeaways": [
        "⭐⭐⭐ Must Know — address translation + page fault",
        "⭐⭐ Important — thrashing",
        "⭐ Good to Know — TLB",
    ],
}

# Legacy aliases must still render via field mapping.
LEGACY = {
    "topic": "HTTP",
    "definition": "HTTP is a request-response protocol for the web.",
    "whyItMatters": ["Lets browsers talk to servers"],
    "importantExamPoints": ["⭐⭐⭐ Request methods"],
    "thirtySecondRevision": ["Client sends request", "Server responds"],
    "vivaQuestions": [{"question": "What is HTTP?", "answer": "HyperText Transfer Protocol."}],
}


def main() -> None:
    assert PROMPT_VERSION.startswith("v18")
    assert is_structured_notes_result(SAMPLE)
    md = structured_notes_to_markdown(SAMPLE)
    assert "# Virtual Memory" in md
    assert "## 1. What is it?" in md
    assert "## 3. Real Life Analogy" in md
    assert "## 7. Visual Diagram" in md
    assert "## 14. Interview / Viva Questions" in md
    assert "## 17. Revision Sheet" in md
    assert "## 18. Key Takeaways" in md
    assert "### Q1." in md
    assert "Paging" in md
    assert "Segmentation" in md

    validate_exam_notes(SAMPLE, markdown=md)

    deduped = deduplicate_structured_notes(
        {
            **SAMPLE,
            "revisionSheet": [
                "VM extends RAM using disk",
                "VM extends RAM using disk",
                "Paging + page tables",
            ],
        }
    )
    assert len(deduped["revisionSheet"]) == 2

    legacy_md = format_exam_notes_markdown(LEGACY)
    assert "## 1. What is it?" in legacy_md
    assert "HTTP" in legacy_md

    print("Professor Alex v18 structured notes checks passed.")
    print(md[:600].encode("ascii", "replace").decode("ascii"), "...")


if __name__ == "__main__":
    main()
