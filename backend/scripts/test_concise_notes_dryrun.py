#!/usr/bin/env python3
"""
Offline dry-run of the Stage-3 concise notes engine — NO network, NO API key.

Feeds a hand-written model payload through the real pipeline (normalize ->
validate -> render -> document gate) so the schema, formatter, and validator
can be checked without burning free-tier quota. Also exercises the repair
path and the rejection paths.

Run from the backend/ directory:
    python scripts/test_concise_notes_dryrun.py
"""

from __future__ import annotations

import asyncio

from app.services.notes_engine.pipeline import ConciseNotesPipeline
from app.services.notes_engine.schema import (
    CONCISE_ENGINE_ID,
    CONCISE_PROMPT_VERSION,
    SECTION_HEADINGS,
)
from app.services.notes_engine.validator import NotesSchemaError, NotesValidationError

GOOD_PAYLOAD = {
    "topic": "Binary Search Tree",
    "definition": (
        "A binary search tree is a binary tree in which every node stores a key, and the keys in a "
        "node's left subtree are smaller than the node's key while the keys in its right subtree are "
        "larger. This ordering lets searches discard half of the remaining tree at each step."
    ),
    "working": [
        "Start the comparison at the root node of the tree.",
        "If the search key equals the current node's key, the search succeeds and stops.",
        "If the search key is smaller, move to the left child; if larger, move to the right child.",
        "Repeat the comparison until a match is found or an empty child pointer is reached.",
        "Insertion follows the same path and attaches the new node at the empty pointer.",
        "Deletion replaces a two-child node with its inorder successor to preserve the ordering.",
    ],
    "advantages": [
        "Search, insert, and delete all run in O(log n) time on a balanced tree.",
        "An inorder traversal returns the keys in sorted order without extra work.",
        "The structure grows dynamically, so no capacity has to be fixed in advance.",
        "Range queries are efficient because subtrees outside the range are skipped.",
    ],
    "disadvantages": [
        "Sorted input degenerates the tree into a linked list with O(n) operations.",
        "Each node carries two pointers, so memory overhead is higher than an array.",
        "Keeping the tree balanced needs extra logic such as AVL or red-black rotations.",
    ],
    "applications": [
        {"name": "Database indexing", "detail": "B-tree variants index table columns for fast lookups."},
        {"name": "Symbol tables", "detail": "Compilers store identifiers and their attributes for quick access."},
        {"name": "Routing tables", "detail": "Network routers match destination prefixes using ordered trees."},
        {"name": "File systems", "detail": "Directory entries are kept ordered for fast name resolution."},
    ],
    "example": (
        "Insert 50, 30, 70, 20, 40 into an empty tree. 50 becomes the root, 30 goes left of 50, 70 goes "
        "right of 50, 20 goes left of 30, and 40 goes right of 30. Searching for 40 compares 40 < 50 "
        "(go left), 40 > 30 (go right), and finds 40 in three comparisons instead of five."
    ),
    "quick_revision": [
        "Left subtree keys < node key < right subtree keys.",
        "Balanced height gives O(log n) search, insert, and delete.",
        "Worst case O(n) when keys arrive already sorted.",
        "Inorder traversal outputs keys in ascending order.",
        "Delete a two-child node using its inorder successor.",
    ],
}

THIN_PAYLOAD = {
    "topic": "Binary Search Tree",
    "definition": "A tree.",
    "working": ["Compare keys."],
    "advantages": ["Fast."],
    "disadvantages": [],
    "applications": [],
    "example": "N/A",
    "quick_revision": [],
}


def _stub(*payloads):
    """Return a generate_notes_json callable that replays payloads in order."""
    queue = list(payloads)
    calls: list[dict] = []

    async def _generate(system_prompt, user_prompt, schema, max_tokens, temperature):
        calls.append({"system": system_prompt, "user": user_prompt, "max_tokens": max_tokens})
        return queue.pop(0), {"provider": "stub", "model": "stub-model"}

    return _generate, calls


async def test_happy_path() -> str:
    generate, calls = _stub(GOOD_PAYLOAD)
    result, metadata = await ConciseNotesPipeline().run(
        topic="Binary Search Trees", subject="Data Structures", generate_notes_json=generate
    )

    notes = result["notes"]
    assert len(calls) == 1, f"expected exactly ONE model call, got {len(calls)}"
    assert metadata["notes_engine"] == CONCISE_ENGINE_ID
    assert metadata["prompt_version"] == CONCISE_PROMPT_VERSION
    assert metadata["gemini_calls"] == 1 and metadata["repaired"] is False

    headings = [line for line in notes.splitlines() if line.startswith("#")]
    assert headings[0].startswith("# "), headings[0]
    assert [h[3:] for h in headings[1:]] == list(SECTION_HEADINGS), headings

    assert 200 <= result["word_count"] <= 800, result["word_count"]
    assert metadata["word_count_status"] in {"on_target", "under_target", "over_target"}
    assert set(result["structured"]) >= {"definition", "working", "quick_revision"}

    # Subject + topic only: no PYQ/RAG text may reach the model. (The system
    # prompt does name PYQs — in the rule forbidding them — so only the user
    # message, which carries the dynamic inputs, is checked.)
    user_prompt = calls[0]["user"].lower()
    assert "subject: data structures" in user_prompt and "topic: binary search tree" in user_prompt
    for banned in ("previous year", "pyq", "marks", "uploaded", "retrieved", "priority"):
        assert banned not in user_prompt, f"user prompt leaked {banned!r}"

    print(
        f"PASS happy path: 1 call, {result['word_count']} words, "
        f"status={metadata['word_count_status']}, all 7 headings present"
    )
    return notes


async def test_repair_path() -> None:
    generate, calls = _stub(THIN_PAYLOAD, GOOD_PAYLOAD)
    result, metadata = await ConciseNotesPipeline().run(
        topic="Binary Search Trees", subject="Data Structures", generate_notes_json=generate
    )
    assert len(calls) == 2, f"expected a repair call, got {len(calls)}"
    assert metadata["repaired"] is True and metadata["gemini_calls"] == 2
    assert "failed validation" in calls[1]["user"] or "errors" in calls[1]["user"].lower()
    print(f"PASS repair path: thin payload repaired in {len(calls)} calls")


async def test_rejects_garbage() -> None:
    generate, _ = _stub(THIN_PAYLOAD, THIN_PAYLOAD)
    try:
        await ConciseNotesPipeline().run(
            topic="Binary Search Trees", subject="Data Structures", generate_notes_json=generate
        )
    except NotesSchemaError as exc:
        missing = {d.get("field") for d in exc.details if isinstance(d, dict)}
        assert {"definition", "disadvantages", "applications"} <= missing, missing
        print(f"PASS rejects garbage: NotesSchemaError after repair ({len(exc.details)} field errors)")
        return
    raise AssertionError("expected NotesSchemaError for a persistently thin payload")


async def test_unknown_topic() -> None:
    generate, _ = _stub({"status": "UNKNOWN_TOPIC"})
    try:
        await ConciseNotesPipeline().run(
            topic="qwertyuiop", subject="Data Structures", generate_notes_json=generate
        )
    except NotesValidationError as exc:
        assert exc.code == "UNKNOWN_TOPIC", exc.code
        print("PASS unknown topic: refusal surfaced as UNKNOWN_TOPIC")
        return
    raise AssertionError("expected UNKNOWN_TOPIC to raise")


async def main() -> int:
    notes = await test_happy_path()
    await test_repair_path()
    await test_rejects_garbage()
    await test_unknown_topic()

    print("\n---- RENDERED MARKDOWN ----")
    print(notes)
    print("\nAll concise-notes dry-run checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
