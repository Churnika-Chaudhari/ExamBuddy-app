#!/usr/bin/env python3
"""Quick validation for the notes preprocessing and topic pipeline."""

from app.services.pipeline.notes_pipeline import NotesPipeline
from app.services.pipeline.topic_pipeline import canonical_topic_name, merge_similar_topics

SAMPLE_PYQ = """
UNIVERSITY EXAMINATION — TIME: 3 HOURS — MAX MARKS: 100
Attempt any three questions. All questions carry equal marks.

Q1. Explain the advantages and disadvantages of Virtual Memory. [10 Marks]
Q2. What is Deadlock? Explain its prevention methods. [10M]
Q3. Define TCP/IP. [5 marks]
Q4. Write short note on Virtual Memory working. [10 Marks]
Q5. Explain need of Virtual Memory in operating system. [10 Marks]
CO1 — Unit 3
OR
Q6. Describe process scheduling algorithms. [10 Marks]
"""

def main() -> None:
    pipeline = NotesPipeline()
    result = pipeline.run(SAMPLE_PYQ, subject="Operating Systems", num_documents=1)

    print("=== Cleaned text (first 500 chars) ===")
    print(result.cleaned_text[:500])
    print("\n=== Question lines ===")
    for line in result.question_lines:
        print(f"  - {line}")

    print("\n=== Extracted topics ===")
    for row in result.topic_analysis.get("topic_table", []):
        print(f"  - {row['topic']} (freq={row['frequency']}, {row['importance']})")

    # Merge tests
    merged = merge_similar_topics({
        "Virtual Memory": 2,
        "Advantages of Virtual Memory": 1,
        "Working of Virtual Memory": 1,
        "Deadlock": 1,
        "Deadlock Prevention": 1,
    })
    print("\n=== Merge test ===")
    for topic, freq in sorted(merged.items(), key=lambda x: -x[1]):
        print(f"  - {topic}: {freq}")

    assert canonical_topic_name("Explain Virtual Memory") != "Explain Virtual Memory"
    assert "Virtual Memory" in merged
    topics = [r["topic"] for r in result.topic_analysis.get("topic_table", [])]
    assert any("Virtual Memory" in t for t in topics), f"Expected Virtual Memory in {topics}"
    assert not any(t.lower().startswith("explain") for t in topics)
    print("\nAll pipeline checks passed.")


if __name__ == "__main__":
    main()
