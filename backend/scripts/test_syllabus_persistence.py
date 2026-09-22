#!/usr/bin/env python3
"""
Syllabus persistence + subject-matching checks against a scratch MongoDB.

Covers what the syllabus -> Home -> (later) PYQ flow depends on:
  - a parsed syllabus is stored under user_id + subject
  - re-uploading the same subject upserts instead of duplicating
  - a PYQ subject finds the syllabus through curated aliases (DBMS ↔
    Database Management System) but never through a loose match
  - a subject with no syllabus reports no modules rather than borrowing one

Run from the backend/ directory (uses MONGODB_URI, writes to a scratch db):
    python scripts/test_syllabus_persistence.py
"""

from __future__ import annotations

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.repositories.syllabus_repository import SyllabusRepository
from app.services.syllabus_service import SyllabusService
from app.utils.syllabus_parser import extract_syllabus_structure

SCRATCH_DB = "smartstudy_syllabus_selftest"
USER_ID = "64b7f9c2e1a4d5b6c7a80001"
OTHER_USER_ID = "64b7f9c2e1a4d5b6c7a80002"

DBMS_SYLLABUS = """
Subject: Database Management System
MODULE I
Introduction to Databases
- DBMS Architecture
- Data Models
MODULE II
Relational Model
- Relational Algebra
- SQL Queries
MODULE III
Normalization
- Functional Dependency
- Normal Forms BCNF
MODULE IV
Transaction Management
- Concurrency Control
- Deadlock Handling
MODULE V
Indexing and Hashing
- B Trees
- Hashing Techniques
"""

CN_SYLLABUS = """
Subject: Computer Networks
UNIT I
Physical Layer
- Transmission Media
- Signal Encoding
UNIT II
Data Link Layer
- Error Detection
- Flow Control
UNIT III
Network Layer
- IP Addressing
- Routing Algorithms
UNIT IV
Transport Layer
- TCP Congestion Control
- UDP
"""


async def main() -> int:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client[SCRATCH_DB]
    await db.syllabi.drop()

    service = SyllabusService(SyllabusRepository(db))

    # 1. Upload a DBMS syllabus with "DBMS" typed in the subject field.
    structure = extract_syllabus_structure(DBMS_SYLLABUS, default_subject="DBMS")
    rows = await service.save_from_structure(
        USER_ID,
        structure,
        default_subject="DBMS",
        file_reference={"document_id": "doc1", "file_name": "dbms_syllabus.pdf"},
        source_document_id="doc1",
    )
    assert len(rows) == 1, f"expected one syllabus row, got {len(rows)}"
    saved = rows[0]
    assert saved["module_count"] == 5, saved["module_count"]
    assert saved["file_reference"]["file_name"] == "dbms_syllabus.pdf"
    assert saved["created_at"] and saved["updated_at"]
    print(
        "PASS save: subject=%s modules=%d topics=%d"
        % (saved["subject"], saved["module_count"], saved["topic_count"])
    )

    # 2. Re-upload the same subject under its long name — must upsert, not duplicate.
    structure2 = extract_syllabus_structure(
        DBMS_SYLLABUS, default_subject="Database Management Systems"
    )
    await service.save_from_structure(
        USER_ID, structure2, default_subject="Database Management Systems"
    )
    assert await db.syllabi.count_documents({}) == 1, "re-upload created a duplicate row"
    print("PASS upsert: re-uploading the same subject keeps exactly one row")

    # 3. A second subject is a separate row, and module count follows the file.
    await service.save_from_structure(
        USER_ID,
        extract_syllabus_structure(CN_SYLLABUS, default_subject="Computer Networks"),
        default_subject="Computer Networks",
    )
    syllabi = await service.list_syllabi(USER_ID)
    assert len(syllabi) == 2, [s["subject"] for s in syllabi]
    counts = {s["subject"]: s["module_count"] for s in syllabi}
    assert sorted(counts.values()) == [4, 5], counts
    print("PASS dynamic module count: %s" % counts)

    # 4. Subject matching for a PYQ uploaded later.
    for spelling in ("DBMS", "dbms", "Database Management System", "Database Management Systems"):
        modules = await service.find_modules_for_subject(USER_ID, spelling)
        assert len(modules) == 5, f"{spelling} -> {len(modules)} modules"
    assert await service.find_modules_for_subject(USER_ID, "Data Mining") == []
    assert await service.find_modules_for_subject(USER_ID, "Operating System") == []
    print("PASS matching: alias spellings resolve, unrelated subjects do not")

    # 5. Syllabi are per user.
    assert await service.list_syllabi(OTHER_USER_ID) == []
    assert await service.find_modules_for_subject(OTHER_USER_ID, "DBMS") == []
    print("PASS isolation: another user sees none of these syllabi")

    # 6. Deleting one leaves the other.
    await service.delete_syllabus(USER_ID, syllabi[0]["id"])
    assert len(await service.list_syllabi(USER_ID)) == 1
    print("PASS delete: only the targeted syllabus is removed")

    await client.drop_database(SCRATCH_DB)
    client.close()
    print("\nAll syllabus persistence checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
