#!/usr/bin/env python3
"""Validate notes sanitizer and structured renderer."""

from app.services.ai.notes_sanitizer import sanitize_note_text, sanitize_rag_passage
from app.services.ai.notes_structured import structured_notes_to_markdown

DIRTY = """
# DML Commands
> FROM UPLOADED DOCUMENTS
[Source 1: 51423_DBMS_PYQ.pdf (pyq)]
Subject Code: 51423
## Definition
DML commands manipulate data.
"""

CLEAN_SAMPLE = {
    "topic": "DML Commands",
    "definition": "DML (Data Manipulation Language) commands modify data stored in database tables.",
    "conceptualExplanation": "DML includes INSERT, UPDATE, DELETE, and SELECT. INSERT adds rows, UPDATE modifies rows, DELETE removes rows.",
    "practicalExamples": "INSERT INTO student VALUES (1, 'Anita', 85);\nUPDATE student SET marks = 90 WHERE id = 1;",
    "summary": "DML commands change and retrieve table data.",
}


def main() -> None:
    cleaned = sanitize_note_text(DIRTY)
    assert "FROM UPLOADED" not in cleaned
    assert "51423" not in cleaned
    assert "[Source 1:" not in cleaned
    assert "DML Commands" in cleaned

    rag = sanitize_rag_passage("[Source 1: file.pdf]\n51423\nINSERT INTO t VALUES (1);")
    assert "[Source" not in rag
    assert "INSERT INTO" in rag

    md = structured_notes_to_markdown(CLEAN_SAMPLE)
    assert "# DML Commands" in md
    assert "## Definition" in md
    assert "## Conceptual Explanation" in md
    assert "## Practical Examples" in md
    assert "INSERT INTO" in md

    print("Notes sanitizer checks passed.")


if __name__ == "__main__":
    main()
