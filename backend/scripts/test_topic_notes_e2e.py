"""End-to-end test for topic notes generation and MongoDB upsert."""
from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()


async def main() -> int:
    from app.core.config import reload_settings
    from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database
    from app.repositories.generated_notes_repository import GeneratedNotesRepository
    from app.services.ai.ai_service import AIService
    from app.services.notes_service import NotesService
    from app.repositories.analysis_repository import AnalysisRepository
    from app.repositories.document_repository import DocumentRepository
    from app.repositories.notes_repository import NotesRepository
    from app.repositories.stats_repository import StatsRepository

    reload_settings()
    await connect_to_mongo()
    db = get_database()

    notes_repo = NotesRepository(db)
    analysis_repo = AnalysisRepository(db)
    document_repo = DocumentRepository(db)
    stats_repo = StatsRepository(db)
    generated_repo = GeneratedNotesRepository(db)
    ai = AIService()

    service = NotesService(
        notes_repo, analysis_repo, document_repo, stats_repo, generated_repo, ai
    )

    user_id = "674a1f2d3b4c5d6e7f8a9b01"
    topic = "Cloud Computing"

    try:
        result = await service.generate_topic_note(
            user_id,
            topic,
            subject="Information Technology",
            regenerate=True,
        )
        notes_len = len(result.get("notes") or "")
        provider = (result.get("ai_metadata") or {}).get("provider")
        print(f"OK: notes_len={notes_len} provider={provider} id={result.get('id')}")
        if notes_len < 100:
            print("FAIL: notes too short")
            return 1
        if not result.get("id"):
            print("FAIL: no note id")
            return 1

        pdf_bytes, filename = await service.export_generated_note_pdf(
            result["id"], user_id
        )
        if len(pdf_bytes) < 500:
            print(f"FAIL: PDF too small ({len(pdf_bytes)} bytes)")
            return 1
        print(f"OK: pdf={filename} size={len(pdf_bytes)}")
        return 0
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
